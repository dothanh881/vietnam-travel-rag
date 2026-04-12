from langfuse import observe

class TravelRAGPipeline:
    def __init__(self, retriever, llm_generator, reranker=None):
        self.retriever = retriever
        self.llm_generator = llm_generator
        self.reranker = reranker

    @observe(name="ViVu_RAG_Pipeline")
    def ask(self, question: str, top_k: int = 5, destination: str = None):
        # Nếu có reranker, lấy rộng ra 15 chunks từ Qdrant để reranker có nhiều dữ liệu
        retrieval_top_k = 15 if self.reranker else top_k

        # 1. Truy xuất dữ liệu từ Qdrant (Truyền toàn bộ thông số xuống Retriever)
        chunks = self.retriever.retrieve(
            query=question,
            top_k=retrieval_top_k,
            destination=destination
        )

        # Rerank lại các chunks và chọn ra top_k tốt nhất
        if self.reranker:
            chunks = self.reranker.rerank(query=question, candidates=chunks, top_n=top_k)

        # 2. Sinh câu trả lời từ LLM
        answer = self.llm_generator.generate_answer(question, chunks)

        # 3. Trả về cả câu trả lời VÀ danh sách nguồn dữ liệu
        return answer, chunks

    @observe(name="ViVu_RAG_Pipeline")
    async def ask_stream(self, question: str, top_k: int = 5, destination: str = None):
        # Nếu có reranker, lấy rộng ra 15 chunks từ Qdrant để reranker có nhiều dữ liệu
        retrieval_top_k = 15 if self.reranker else top_k

        # 1. Truy xuất dữ liệu từ Qdrant (Synchronous, chạy trong threadpool để không block ASYNC EVENT LOOP)
        import time
        from fastapi.concurrency import run_in_threadpool
        
        t1 = time.time()
        chunks = await run_in_threadpool(
            self.retriever.retrieve,
            query=question,
            top_k=retrieval_top_k,
            destination=destination
        )
        t2 = time.time()
        print(f"DEBUG: Retrieval took {t2-t1:.2f}s")

        # Rerank lại các chunks (Synchronous, chạy trong threadpool để không block ASYNC EVENT LOOP)
        if self.reranker:
            tr1 = time.time()
            chunks = await run_in_threadpool(
                self.reranker.rerank,
                query=question,
                candidates=chunks,
                top_n=top_k
            )
            tr2 = time.time()
            print(f"DEBUG: Reranking took {tr2-tr1:.2f}s")

        # 2. Truyền sang generator dưới dạng luồng
        return self.llm_generator.generate_answer_stream(question, chunks), chunks
