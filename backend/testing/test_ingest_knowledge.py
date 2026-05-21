import os
import sys

# Thêm thư mục gốc vào PYTHONPATH để tránh lỗi import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.ingest_runner import IngestRunner
from core.logger import get_logger

logger = get_logger(__name__)


def run_test_ingest():
    # 1. Định nghĩa đường dẫn tới file JSON Layer 3 đã chuẩn bị [cite: 121]
    json_path = "../dataset_builder/data/chunks/angiang_chunks.json"

    # Kiểm tra file tồn tại trước khi chạy
    if not os.path.exists(json_path):
        logger.error(f"Không tìm thấy file dữ liệu tại: {json_path}")
        return

    try:
        # 2. Khởi tạo Pipeline (Người điều phối)
        # Pipeline này sẽ tự gọi KnowledgeLoader và TravelVectorStore bên trong
        pipeline = IngestRunner()

        logger.info("--- BẮT ĐẦU LUỒNG TEST INGESTION ---")

        # 3. Chạy luồng nạp dữ liệu
        # Sử dụng API run_batch
        result = pipeline.run_batch(destination="an-giang", category="*", file_name="angiang_chunks.json")

        # 4. Kiểm tra kết quả
        if result > 0:
            logger.info(f"THÀNH CÔNG: Đã nạp {result} điểm dữ liệu An Giang vào Qdrant.")
        else:
            logger.warning("CẢNH BÁO: Quá trình chạy không có lỗi nhưng không có dữ liệu nào được nạp.")

    except Exception as e:
        logger.error(f"LỖI HỆ THỐNG khi đang nạp dữ liệu: {str(e)}")


if __name__ == "__main__":
    run_test_ingest()
