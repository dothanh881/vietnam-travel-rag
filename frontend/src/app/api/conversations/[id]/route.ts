import { NextResponse } from 'next/server';
import { currentUser } from '@clerk/nextjs/server';
import prisma from '@/lib/prisma';

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: conversationId } = await params;

    const user = await currentUser();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Lấy tin nhắn và kiểm tra quyền sở hữu
    const conversation = await prisma.conversation.findUnique({
      where: { id: conversationId },
      include: {
        messages: {
          orderBy: { createdAt: 'asc' },
          select: { id: true, role: true, content: true }
        }
      }
    });

    if (!conversation) {
      return NextResponse.json({ error: 'Không tìm thấy' }, { status: 404 });
    }

    if (conversation.userId !== user.id) {
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }

    return NextResponse.json(conversation);
  } catch (error) {
    console.error('Lỗi khi lấy tin nhắn:', error);
    return NextResponse.json({ error: 'Lỗi server' }, { status: 500 });
  }
}
