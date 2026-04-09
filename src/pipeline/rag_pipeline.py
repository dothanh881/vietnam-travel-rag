class TravelRAGPipeline:
    def __init__(self, retriever, llm_generator, reranker=None):
        self.retriever = retriever
        self.llm_generator = llm_generator
        self.reranker = reranker

    async def ask_stream(self, question: str, top_k: int = 5, destination: str = None, category: str = None):
        # 1. Truy xuất dữ liệu từ Qdrant
        retrieval_top_k = 15 if self.reranker else top_k
        chunks = self.retriever.retrieve(
            query=question,
            top_k=retrieval_top_k,
            destination=destination,
            category=category
        )

        # 2. Reranking (Nếu có bộ lọc Cohere)
        if self.reranker:
            chunks = self.reranker.rerank(
                query=question,
                candidates=chunks,
                top_n=top_k
            )

        # 3. Trả về Generator sinh từng token kèm theo danh sách chunks
        # Chúng ta trả về chunks ngay lập tức để UI có thể hiển thị nguồn dữ liệu song song
        return self.llm_generator.generate_answer_stream(question, chunks), chunks

    def ask(self, question: str, top_k: int = 5, destination: str = None, category: str = None):
        # 1. Truy xuất dữ liệu từ Qdrant
        # Lấy nhiều kết quả hơn để Reranker có dữ liệu lọc (tăng top_k lên 15)
        retrieval_top_k = 15 if self.reranker else top_k
        chunks = self.retriever.retrieve(
            query=question,
            top_k=retrieval_top_k,
            destination=destination,
            category=category
        )

        # 2. Reranking (Nếu có bộ lọc Cohere)
        if self.reranker:
            chunks = self.reranker.rerank(
                query=question,
                candidates=chunks,
                top_n=top_k
            )

        # 3. Sinh câu trả lời từ LLM
        answer = self.llm_generator.generate_answer(question, chunks)

        # 4. Trả về cả câu trả lời VÀ danh sách nguồn dữ liệu
        return answer, chunks