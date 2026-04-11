// Route handler proxy SSE cho FastAPI - tuân thủ Vercel AI Data Stream Protocol v1
export async function POST(req: Request) {
    try {
        const { messages, mode = "vllm", top_k = 3 } = await req.json();

        // Lấy tin nhắn mới nhất
        const latestMessage = messages[messages.length - 1];
        if (!latestMessage || latestMessage.role !== 'user') {
            return makeStreamResponse('Thiếu tin nhắn người dùng.');
        }

        // Forward sang FastAPI backend
        const backendRes = await fetch("http://localhost:8000/api/v1/chat/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                query: latestMessage.content,
                mode: mode,
                top_k: top_k
            })
        });

        if (!backendRes.ok) {
            return makeStreamResponse(`⚠️ Backend lỗi (HTTP ${backendRes.status}). Hãy kiểm tra FastAPI server.`);
        }

        // Tạo ReadableStream thủ công để đọc SSE từ FastAPI và re-encode sang Vercel AI Data Stream Protocol
        const readable = new ReadableStream({
            async start(controller) {
                const reader = backendRes.body!.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

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
                                    controller.enqueue(
                                        new TextEncoder().encode('0:' + JSON.stringify(parsed.data) + '\n')
                                    );
                                } else if (parsed.type === 'error' && parsed.data) {
                                    controller.enqueue(
                                        new TextEncoder().encode('0:' + JSON.stringify(`\n\n🚨 Lỗi: ${parsed.data}`) + '\n')
                                    );
                                }
                                // 'status' và 'sources' bỏ qua - không gửi lên UI
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
