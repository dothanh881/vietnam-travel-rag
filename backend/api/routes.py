import time
import os
import glob
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from functools import lru_cache
import json
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
from retrieval.reranker import CohereReranker
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from service.state_manager import TravelStateManager

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

    NGROK_URL = "https://unpatrician-underogatively-bronson.ngrok-free.dev/v1" 

    return LLMGenerator(
        mode="vllm", # Mặc định
        vllm_model="qwen-vivu", 
        vllm_base_url=NGROK_URL,
        vllm_api_key="sk-runpod-key",
        ollama_model="hf.co/thanhdo881/qwen3-1.7b-vivu-travel-vn-GGUF:Q4_K_M"
    )

@lru_cache(maxsize=1)
def get_reranker() -> CohereReranker:
    # Bật lại Reranker, sử dụng Cohere Siêu tốc độ trên Cloud
    return CohereReranker()

@lru_cache(maxsize=1)
def get_rag_pipeline() -> TravelRAGPipeline:
    return TravelRAGPipeline(
        retriever=get_retriever(),
        llm_generator=get_llm_generator(),
        reranker=get_reranker()
    )

@lru_cache(maxsize=1)
def get_state_manager() -> TravelStateManager:
    return TravelStateManager()



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
        # Cập nhật chế độ chạy dựa trên yêu cầu từ UI
        generator.mode = request.mode

        answer, raw_chunks = pipeline.ask(
            question=request.query,
            top_k=request.top_k,
            destination=None
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


@router.post("/chat/stream", tags=["RAG Chat Stream"])
def chat_stream_endpoint(
        request: ChatRequest,
        background_tasks: BackgroundTasks,
        pipeline: TravelRAGPipeline = Depends(get_rag_pipeline),
        generator: LLMGenerator = Depends(get_llm_generator),
        state_manager: TravelStateManager = Depends(get_state_manager)
):
    # --- START REDIS STATE MANAGEMENT ---
    active_dest = None
    if request.session_id and request.session_id != "guest_session":
        state = state_manager.get_state(request.session_id)
        active_dest = state.get("active")
    
    # Trích xuất địa danh hiện tại bằng Analyzer (Zero-LLM) để check
    analyzer_result = pipeline.retriever.analyzer.analyze(request.query)
    current_dest = analyzer_result.get("destination")
    
    # Nếu câu hỏi hiện hành MẬP MỜ (không có dest) -> Fallback dùng active_dest từ Redis
    target_dest = current_dest if current_dest else active_dest
    
    if not current_dest and active_dest:
        print(f"[Redis State] Context Switching: Khôi phục ngữ cảnh '{active_dest}' cho câu hỏi mập mờ.")
    # --- END REDIS STATE MANAGEMENT ---
    
    async def event_generator():
        start_time = time.time()
        try:
            # Cập nhật chế độ chạy dựa trên yêu cầu từ UI
            generator.mode = request.mode
            
            # 1. Báo cáo trạng thái ngay để mở luồng mượt mà
            yield f"data: {json.dumps({'type': 'status', 'data': f'* Đang tìm kiếm tài liệu (Chế độ: {generator.mode})...* ⏳'})}\n\n"
            
            # 2. Bắt đầu quá trình RAG
            answer_stream, raw_chunks = await pipeline.ask_stream(
                question=request.query,
                top_k=request.top_k,
                destination=target_dest
            )
            
            # 1. Gửi Cấu trúc Nguồn dữ liệu (Sources) trước
            sources = []
            for c in raw_chunks:
                sources.append({
                    "text": c.get("text", ""),
                    "destination": c.get("destination"),
                    "category": c.get("category"),
                    "score": float(c.get("score", 0.0)),
                    "rerank_score": c.get("rerank_score")
                })
                
            yield f"data: {json.dumps({'type': 'sources', 'data': sources})}\n\n"
            
            # 2. Bắt đầu đẩy nội dung stream từ LLM về và tính toán thời gian
            first_token_lat = None
            async for token in answer_stream:
                if first_token_lat is None:
                    first_token_lat = round(time.time() - start_time, 2)
                    yield f"data: {json.dumps({'type': 'status', 'data': f'*  Tốc độ phản hồi (TTFT): {first_token_lat}s*'})}\n\n"
                
                # Đóng gói an toàn để tránh break JSON
                yield f"data: {json.dumps({'type': 'token', 'data': token})}\n\n"
                
            total_process_time = round(time.time() - start_time, 2)
            yield f"data: {json.dumps({'type': 'status', 'data': f'*  Tổng thời gian: {total_process_time}s*'})}\n\n"
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': f'Lỗi hệ thống: {str(e)}'})}\n\n"

    # Gắn BackgroundTask cập nhật Redis State ẩn sử dụng tham số Zero-LLM (rất siêu tốc)
    if request.session_id and request.session_id != "guest_session":
        # Khai báo hàm helper nhỏ gọn để in log
        def update_redis_fast():
            state_manager.update_context(session_id=request.session_id, new_destination=target_dest)
            print(f"[Redis State] Đã ghi nhận State mới chạy ngầm: {target_dest}")
            
        background_tasks.add_task(update_redis_fast)

    return StreamingResponse(event_generator(), media_type="text/event-stream", background=background_tasks)


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
