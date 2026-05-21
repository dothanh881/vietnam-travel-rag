from service.embedding import EmbeddingService
from retrieval.retriever import TravelRetriever
from retrieval.search import VectorSearchEngine
from retrieval.query_analyzer import TravelQueryAnalyzer
from generator.llm import LLMGenerator
from pipeline.rag_pipeline import TravelRAGPipeline
from vector_store.qdrant import TravelVectorStore
from retrieval.reranker import Reranker

from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
import torch


def load_qwen_baseline(model_id="Qwen/Qwen2.5-3B-Instruct"):
    import torch

    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)

    # Xác định device an toàn
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Load model không dùng BitsAndBytes để tránh lỗi CPU
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32,
        low_cpu_mem_usage=True,
        device_map=device,
        trust_remote_code=True
    )

    model.eval()
    return model, tokenizer, device


def main():
    print(" Initializing Travel RAG System...")

    # -------- Load model --------
    # model, tokenizer, current_device = load_qwen_baseline("Qwen/Qwen2.5-3B-Instruct")

    # -------- Init components --------
    embedding = EmbeddingService()

    vector_store = TravelVectorStore()
    search_engine = VectorSearchEngine(vector_store)

    # Nhập URL Ngrok nếu bạn chạy test CLI
    NGROK_URL = "https://<xxxx-xxxx>.ngrok-free.app/v1"
    llm_generator = LLMGenerator(
        ollama_model="qwen-vivu", 
        base_url=NGROK_URL, 
        api_key="sk-runpod-key"
    )

    analyzer = TravelQueryAnalyzer()

    retriever = TravelRetriever(
        embedding_service=embedding,
        search_engine=search_engine,
        analyzer=analyzer
    )

    reranker = Reranker()

    rag_pipeline = TravelRAGPipeline(
        retriever=retriever,
        llm_generator=llm_generator,
        reranker=reranker
    )

    print(" System ready! Type 'exit' to quit.\n")

    # -------- Chat loop --------
    while True:
        question = input(" User: ")

        if question.lower() in ["exit", "quit"]:
            print(" Bye!")
            break

        answer, chunks = rag_pipeline.ask(question)

        print(f" Bot: {answer}\n")


#  QUAN TRỌNG
if __name__ == "__main__":
    main()
