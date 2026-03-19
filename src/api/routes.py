import time
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

router = APIRouter()


# ==========================================
# DEPENDENCY INJECTION (Singleton)
# ==========================================

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
        analyzer=TravelQueryAnalyzer()
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