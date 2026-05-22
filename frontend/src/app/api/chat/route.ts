// Route handler proxy SSE cho FastAPI - tuân thủ Vercel AI Data Stream Protocol v1
// Tăng timeout lên 60s để hỗ trợ LLM streaming (mặc định Vercel chỉ 10s)
export const maxDuration = 60;

import { getServerSession } from "next-auth/next";
import { authOptions } from "@/app/api/auth/[...nextauth]/route";
import prisma from "@/lib/prisma";

export async function POST(req: Request) {
    try {
        const { messages, mode = "vllm", top_k = 3, conversationId: reqConversationId } = await req.json();

        // Lấy tin nhắn mới nhất
        const latestMessage = messages[messages.length - 1];
        if (!latestMessage || latestMessage.role !== 'user') {
            return makeStreamResponse('Thiếu tin nhắn người dùng.');
        }

        const session = await getServerSession(authOptions);
        const userId = session?.user ? (session.user as any).id : null;

        // Tạo biến session (Hỗ trợ Guest giữ context)
        let dbConversationId = reqConversationId;
        
        // --- LƯU VÀO DATABASE (NẾU ĐĂNG NHẬP) ---
        if (userId) {
            if (!dbConversationId) {
                // Cuộc trò chuyện mới
                const title = latestMessage.content.substring(0, 45) + (latestMessage.content.length > 45 ? '...' : '');
                const newConv = await prisma.conversation.create({
                    data: {
                        userId: userId,
                        title: title,
                    }
                });
                dbConversationId = newConv.id;
            }
            
            // Lưu tin nhắn của User
            await prisma.message.create({
                data: {
                    conversationId: dbConversationId,
                    role: 'user',
                    content: latestMessage.content
                }
            });
        } else if (!dbConversationId) {
            // Khách vãn lai
            dbConversationId = "guest_" + crypto.randomUUID();
        }

        // --- FORWARD SANG FASTAPI ---
        const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const backendRes = await fetch(`${backendUrl}/api/v1/chat/stream`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                query: latestMessage.content,
                history: messages.slice(0, -1),
                mode: mode,
                top_k: top_k,
                session_id: dbConversationId
            })
        });

        if (!backendRes.ok) {
            return makeStreamResponse(`⚠️ Backend lỗi (HTTP ${backendRes.status}). Hãy kiểm tra FastAPI server.`);
        }

        // --- XỬ LÝ TRẢ VỀ & NHẬN TOÀN BỘ AI MESSAGE ---
        const readable = new ReadableStream({
            async start(controller) {
                // Gửi ID về frontend cho cả User lẫn Guest để giữ Context Switching
                if (dbConversationId && !reqConversationId) {
                    const convData = { conversationId: dbConversationId };
                    controller.enqueue(new TextEncoder().encode(`8:${JSON.stringify(convData)}\n`));
                }

                const reader = backendRes.body!.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                let fullAiResponse = '';

                try {
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;

                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\n');
                        buffer = lines.pop() ?? ''; // giữ lại dòng chưa hoàn chỉnh

                        for (const line of lines) {
                            const trimmed = line.trim();
                            if (!trimmed.startsWith('data: ')) continue;

                            const dataStr = trimmed.slice(6).trim();
                            if (dataStr === '[DONE]') continue;

                            try {
                                const parsed = JSON.parse(dataStr);

                                if (parsed.type === 'token' && parsed.data) {
                                    // Chuẩn Vercel AI Data Stream: 0:"text"\n
                                    fullAiResponse += parsed.data;
                                    controller.enqueue(
                                        new TextEncoder().encode('0:' + JSON.stringify(parsed.data) + '\n')
                                    );
                                } else if (parsed.type === 'budget_chart' && parsed.data) {
                                    // Gửi budget data qua 8: metadata event
                                    controller.enqueue(
                                        new TextEncoder().encode('8:' + JSON.stringify([{ type: 'budget_chart', data: parsed.data }]) + '\n')
                                    );
                                } else if (parsed.type === 'error' && parsed.data) {
                                    controller.enqueue(
                                        new TextEncoder().encode('0:' + JSON.stringify(`\n\n🚨 Lỗi: ${parsed.data}`) + '\n')
                                    );
                                }
                            } catch (_) {
                                // Bỏ qua dòng không parse được
                            }
                        }
                    }
                } catch (err) {
                    controller.enqueue(
                        new TextEncoder().encode('0:' + JSON.stringify(`⚠️ Lỗi kết nối stream: ${err}`) + '\n')
                    );
                } finally {
                    // --- LƯU TIN NHẮN CỦA AI VÀO DB NẾU CÓ ĐĂNG NHẬP ---
                    if (userId && dbConversationId && fullAiResponse) {
                        try {
                            await prisma.message.create({
                                data: {
                                    conversationId: dbConversationId,
                                    role: 'assistant',
                                    content: fullAiResponse
                                }
                            });
                        } catch (dbErr) {
                            console.error("Lỗi lưu tin nhắn AI:", dbErr);
                        }
                    }

                    // Gửi gói kết thúc BẮT BUỘC theo Vercel AI Data Stream Protocol v1
                    controller.enqueue(
                        new TextEncoder().encode('e:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n')
                    );
                    controller.enqueue(
                        new TextEncoder().encode('d:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n')
                    );
                    controller.close();
                }
            }
        });

        return new Response(readable, {
            headers: {
                'Content-Type': 'text/plain; charset=utf-8',
                'x-vercel-ai-data-stream': 'v1',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            }
        });

    } catch (error) {
        return makeStreamResponse(`⚠️ Lỗi hệ thống: ${error}`);
    }
}

/** Helper: tạo response lỗi theo chuẩn Vercel AI Data Stream */
function makeStreamResponse(message: string): Response {
    const body = [
        '0:' + JSON.stringify(message) + '\n',
        'e:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n',
        'd:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n',
    ].join('');

    return new Response(body, {
        headers: {
            'Content-Type': 'text/plain; charset=utf-8',
            'x-vercel-ai-data-stream': 'v1',
        }
    });
}
