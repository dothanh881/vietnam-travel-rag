import { NextResponse } from 'next/server';
import { currentUser } from '@clerk/nextjs/server';
import prisma from '@/lib/prisma';

export async function GET() {
  try {
    const user = await currentUser();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const conversations = await prisma.conversation.findMany({
      where: { userId: user.id },
      orderBy: { updatedAt: 'desc' },
      select: {
        id: true,
        title: true,
        updatedAt: true,
      }
    });

    return NextResponse.json(conversations);
  } catch (error) {
    console.error('Lỗi khi lấy danh sách hội thoại:', error);
    return NextResponse.json({ error: 'Lỗi server' }, { status: 500 });
  }
}
