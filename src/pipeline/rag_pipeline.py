class TravelRAGPipeline:
    """
    Main RAG Pipeline:
        query → retrieve → generate
    """

    def __init__(self, retriever, llm_generator):
        self.retriever = retriever
        self.llm_generator = llm_generator

    def ask(self, question: str) -> str:
        # 1. retrieve
        chunks = self.retriever.retrieve(question)

        # 2. generate
        answer = self.llm_generator.generate_answer(question, chunks)

        return answer