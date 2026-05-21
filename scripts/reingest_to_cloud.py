import os
import sys

# Thêm thư mục backend vào PYTHONPATH để import được các module của backend
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from ingestion.ingest_runner import IngestRunner
from service.bm25_encoder import TravelBM25Encoder
from core.logger import get_logger

logger = get_logger(__name__)

def run_reingest():
    # 1. Kiểm tra API Keys (Qdrant Cloud & OpenAI)
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", ".env"))
    
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_key:
        logger.error("CHƯA CÓ OPENAI_API_KEY trong file .env!")
        return
        
    if not qdrant_url or "localhost" in qdrant_url:
        logger.warning("QDRANT_URL đang trống hoặc là localhost. Bạn có chắc muốn nạp vào Local không? (Nhấn Ctrl+C để hủy nếu muốn dùng Cloud)")
    elif not qdrant_key:
        logger.warning("Đang dùng Qdrant Cloud nhưng KHÔNG CÓ QDRANT_API_KEY!")

    try:
        # Khởi tạo BM25 Encoder
        bm25 = TravelBM25Encoder()
        
        # 2. Khởi tạo Pipeline (Tự động recreate collection với dimension=1536 cho OpenAI)
        runner = IngestRunner(bm25_encoder=bm25)
        
        # Xóa dữ liệu cũ và tạo collection mới với kích thước vector 1536
        logger.info("Đang tạo lại Collection trên Qdrant với Dimension = 1536...")
        runner.vector_store.recreate_collection()

        logger.info("--- BẮT ĐẦU LUỒNG INGESTION BẰNG OPENAI LÊN QDRANT CLOUD ---")

        # 3. Chạy luồng nạp dữ liệu (Nạp toàn bộ dữ liệu)
        # Sửa file_name="..." nếu bạn chỉ muốn nạp 1 file nhất định
        result = runner.run_batch(destination="*", category="*", file_name="*")

        # 4. Kiểm tra kết quả
        if result > 0:
            logger.info(f"THÀNH CÔNG: Đã nạp {result} chunks vào Qdrant Cloud.")
        else:
            logger.warning("CẢNH BÁO: Không có dữ liệu nào được nạp (Kiểm tra lại thư mục DATA_LAKE).")

    except Exception as e:
        logger.error(f"LỖI HỆ THỐNG khi đang nạp dữ liệu: {str(e)}")

if __name__ == "__main__":
    run_reingest()
