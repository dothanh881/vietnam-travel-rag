class TravelRAGPipeline:
    def __init__(self, retriever, llm_generator):
        self.retriever = retriever
        self.llm_generator = llm_generator

    def ask(self, question: str, top_k: int = 5, destination: str = None, category: str = None):
        # 1. Truy xuất dữ liệu từ Qdrant (Truyền toàn bộ thông số xuống Retriever)
        chunks = self.retriever.retrieve(
            query=question,
            top_k=top_k,
            destination=destination,
            category=category
        )

        # 2. Sinh câu trả lời từ LLM
        answer = self.llm_generator.generate_answer(question, chunks)

        # 3. Trả về cả câu trả lời VÀ danh sách nguồn dữ liệu
        return answer, chunks