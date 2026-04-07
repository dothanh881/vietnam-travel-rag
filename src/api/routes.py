import time
import os
import glob
from fastapi import APIRouter, HTTPException, Depends
from functools import lru_cache
from api.schemas import ChatRequest, ChatResponse, IngestRequest, IngestResponse, SourceChunk
from service.embedding import EmbeddingService
from vector_store.qdrant import TravelVectorStore
from retrieval.search import VectorSearchEngine
from retrieval.query_analyzer import TravelQueryAnalyzer
from retrieval.retriever import TravelRetriever
from generator.llm import LLMGenerator
from pipeline.rag_pipeline import TravelRAGPipeline
from ingestion.ingest_runner import IngestRunner
from service.bm25_encoder import TravelBM25Encoder

router = APIRouter()

# ==========================================
# CONSTANTS FOR INGESTION
# ==========================================
DATA_LAKE_DIR = r"G:\My Drive\DataLake_baseknowledge_rag_KTLN\dataset"
INPUT_DIR = os.path.join(DATA_LAKE_DIR, "documents")  # Nơi chứa Bản ghi Vàng
OUTPUT_DIR = os.path.join(DATA_LAKE_DIR, "chunks")    # Nơi xuất Payload

# ==========================================
# DEPENDENCY INJECTION (Singleton)
# ==========================================

@lru_cache(maxsize=1)
def get_bm25_encoder() -> TravelBM25Encoder:
    return TravelBM25Encoder(vocab_path=os.path.join(DATA_LAKE_DIR, "vocab.json"))

@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()


@lru_cache(maxsize=1)
def get_vector_store() -> TravelVectorStore:
    return TravelVectorStore(collection_name="travel_knowledge_base")


@lru_cache(maxsize=1)
def get_retriever() -> TravelRetriever:
    return TravelRetriever(
        embedding_service=get_embedding_service(),
        search_engine=VectorSearchEngine(get_vector_store()),
        analyzer=TravelQueryAnalyzer(),
        bm25_encoder=get_bm25_encoder()
    )

@lru_cache(maxsize=1)
def get_llm_generator() -> LLMGenerator:
    return LLMGenerator(mode="ollama", ollama_model="hf.co/Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M")


@lru_cache(maxsize=1)
def get_rag_pipeline() -> TravelRAGPipeline:
    return TravelRAGPipeline(
        retriever=get_retriever(),
        llm_generator=get_llm_generator()
    )


# ==========================================
# ENDPOINTS
# ==========================================

@router.post("/chat", response_model=ChatResponse, tags=["RAG Chat"])
def chat_endpoint(
        request: ChatRequest,
        pipeline: TravelRAGPipeline = Depends(get_rag_pipeline),
        generator: LLMGenerator = Depends(get_llm_generator)
):
    start_time = time.time()
    try:
        # Cập nhật mode LLM nếu client có yêu cầu đổi
        generator.mode = request.mode

        # Gọi RAG pipeline (đã được sửa để trả về 2 biến)
        answer, raw_chunks = pipeline.ask(
            question=request.query,
            top_k=request.top_k,
            destination=request.destination,
            category=request.category
        )

        # Ánh xạ (Mapping) dữ liệu thô sang Pydantic Schema
        sources = []
        for c in raw_chunks:
            sources.append(
                SourceChunk(
                    text=c.get("text", ""),
                    destination=c.get("destination"),
                    category=c.get("category"),
                    score=c.get("score", 0.0)
                )
            )

        process_time = round(time.time() - start_time, 2)

        return ChatResponse(
            answer=answer,
            sources=sources,
            processing_time=process_time
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")


@lru_cache(maxsize=1)
def get_ingest_runner() -> IngestRunner:
    return IngestRunner(bm25_encoder=get_bm25_encoder())

@router.post("/ingest", response_model=IngestResponse, tags=["RAG Ingestion"])
def ingest_endpoint(
        request: IngestRequest,
        runner: IngestRunner = Depends(get_ingest_runner)
):
    try:
        # Chuẩn hóa tham số (Nếu người dùng không truyền thì mặc định là "*")
        dest = request.destination or "*"
        cat = request.category or "*"
        file_name = request.file_name or "*"
        
        # Gọi Runner xử lý toàn bộ logic
        total_inserted = runner.run_batch(destination=dest, category=cat, file_name=file_name)
        
        if total_inserted == 0:
            raise HTTPException(status_code=404, detail="Không tìm thấy file nào phù hợp với bộ lọc để Ingest.")
            
        return IngestResponse(
            status="success",
            chunks_inserted=total_inserted
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống khi ingest dữ liệu: {str(e)}")
