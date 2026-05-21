import { NextResponse } from 'next/server';

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    return NextResponse.json({ error: 'Tính năng lưu lịch sử đang tắt ở bản Demo.' }, { status: 401 });
  } catch (error) {
    return NextResponse.json({ error: 'Lỗi server' }, { status: 500 });
  }
}
