import os
import glob
from core.logger import get_logger
from ingestion.knowledge_loader import KnowledgeLoader
from vector_store.qdrant import TravelVectorStore
from service.embedding import EmbeddingService

logger = get_logger(__name__)

# Trỏ tới Data Lake của bạn
OUTPUT_DIR = r"G:\My Drive\DataLake_baseknowledge_rag_KTLN\dataset\chunks"

class IngestRunner:
    def __init__(self, bm25_encoder=None):
        self.vector_store = TravelVectorStore()
        self.embedding_service = EmbeddingService()
        self.bm25_encoder = bm25_encoder
        self.loader = KnowledgeLoader(self.vector_store, self.embedding_service, self.bm25_encoder)

    def run_batch(self, destination: str = "*", category: str = "*", file_name: str = "*") -> int:
        """
        Luồng Ingest linh hoạt: Hỗ trợ nạp Toàn bộ hoặc theo Target Slug.
        """
        # 1. Xây dựng đường dẫn quét file
        # VD: chunks/an-giang/*/ *.json
        target_file = file_name if (file_name and file_name != "*") else "*.json"
        
        # Format lại dest/cat để tránh nối chuỗi rỗng
        dest_folder = destination if destination else "*"
        cat_folder = category if category else "*"
        
        search_path = os.path.join(OUTPUT_DIR, dest_folder, cat_folder, target_file)
        
        files_to_process = glob.glob(search_path)
        
        if not files_to_process:
            return 0 # Không tìm thấy file nào
            
        logger.info(f" Bắt đầu Ingest {len(files_to_process)} file từ thư mục: {destination}/{category}")
        
        # Kiểm tra và fit BM25 nếu chưa fit
        if self.bm25_encoder and not self.bm25_encoder._fitted:
            logger.info("BM25 chưa được fit, tiến hành quét toàn bộ chunks để tạo vocab...")
            all_texts = []
            for file_path in files_to_process:
                try:
                    chunks = self.loader.load_json(file_path)
                    if chunks:
                        all_texts.extend([c.get('chunk_text', '') for c in chunks])
                except Exception as e:
                    logger.error(f"Lỗi đọc file lúc build vocab {file_path}: {str(e)}")
            
            if all_texts:
                self.bm25_encoder.fit(all_texts)
        
        total_inserted = 0
        
        # 2. Xử lý từng file
        for file_path in files_to_process:
            try:
                chunks = self.loader.load_json(file_path)
                if chunks:
                    inserted = self.loader.process_and_store(chunks)
                    total_inserted += inserted
                    logger.info(f" Ingest thành công {inserted} chunks từ {os.path.basename(file_path)}")
            except Exception as e:
                logger.error(f" Lỗi Ingest file {file_path}: {str(e)}")
                
        return total_inserted