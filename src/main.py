from service.embedding import EmbeddingService
from retrieval.retriever import TravelRetriever
from retrieval.search import VectorSearchEngine
from retrieval.query_analyzer import TravelQueryAnalyzer
from generator.llm_generator import LLMGenerator
from pipeline.rag_pipeline import TravelRAGPipeline
from ingestion.qdrant_store import TravelVectorStore

from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch


def load_qwen(base_model_path, lora_path, device="cuda"):
    tokenizer = AutoTokenizer.from_pretrained(base_model_path, trust_remote_code=True)

    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )

    model = PeftModel.from_pretrained(base_model, lora_path)
    model.eval()

    return model, tokenizer


def main():
    print(" Initializing Travel RAG System...")

    # -------- Load model --------
    model, tokenizer = load_qwen(
        base_model_path="path_to_base_model",
        lora_path="path_to_lora"
    )

    # -------- Init components --------
    embedding = EmbeddingService()

    vector_store = TravelVectorStore()
    search_engine = VectorSearchEngine(vector_store)

    analyzer = TravelQueryAnalyzer()

    retriever = TravelRetriever(
        embedding_service=embedding,
        search_engine=search_engine,
        analyzer=analyzer
    )

    llm_generator = LLMGenerator(model, tokenizer)

    rag_pipeline = TravelRAGPipeline(
        retriever=retriever,
        llm_generator=llm_generator
    )

    print(" System ready! Type 'exit' to quit.\n")

    # -------- Chat loop --------
    while True:
        question = input(" User: ")

        if question.lower() in ["exit", "quit"]:
            print(" Bye!")
            break

        answer = rag_pipeline.ask(question)

        print(f" Bot: {answer}\n")


#  QUAN TRỌNG
if __name__ == "__main__":
    main()