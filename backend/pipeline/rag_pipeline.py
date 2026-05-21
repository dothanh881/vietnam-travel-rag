import time
from langfuse import observe
from fastapi.concurrency import run_in_threadpool
from core.logger import get_logger
from core.tools_exec import fetch_real_weather

logger = get_logger(__name__)

class TravelRAGPipeline:
    def __init__(self, retriever, llm_generator, reranker=None):
        self.retriever = retriever
        self.llm_generator = llm_generator
        self.reranker = reranker
        
        self.tools = {
            "search_knowledge_base": self._tool_search_kb,
            "get_weather": self._tool_get_weather,
            "combined": self._tool_combined
        }

    # ---------------------------------------------------------
    # ĐỊNH NGHĨA CÁC HÀM THỰC THI TOOL (TÁCH BIỆT LOGIC)
    # ---------------------------------------------------------
    async def _tool_search_kb(self, query_arg: str, question: str, destination: str = None, top_k: int = 5):
        """Thực thi nghiệp vụ RAG: Tìm kiếm Vector DB và sinh câu trả lời"""
        logger.info(f"[TOOL: RAG] Bắt đầu tìm kiếm vector cho: '{query_arg}'")
        retrieval_top_k = 15 if self.reranker else top_k
        
        t1 = time.time()
        chunks = await run_in_threadpool(
            self.retriever.retrieve,
            query=query_arg,
            top_k=retrieval_top_k,
            destination=destination
        )
        logger.info(f"[TOOL: RAG] Thời gian truy xuất: {time.time()-t1:.2f}s")

        if self.reranker:
            tr1 = time.time()
            chunks = await run_in_threadpool(
                self.reranker.rerank,
                query=query_arg,
                candidates=chunks,
                top_n=top_k
            )
            logger.info(f"[TOOL: RAG] Thời gian Rerank: {time.time()-tr1:.2f}s")

        logger.info("[AGENT] Truyền kết quả RAG cho LLM tổng hợp...")
        stream = self.llm_generator.generate_answer_stream(question, chunks)
        return stream, chunks

    async def _tool_get_weather(self, question: str, location: str = None, date: str = "today", activity: str = None, **kwargs):
        """Thực thi nghiệp vụ Thời Tiết: Gọi API thực tế và suy luận du lịch"""
        if not location and "query_arg" in kwargs:
            location = kwargs.pop("query_arg")
            
        logger.info(f"[TOOL: WEATHER] Đang lấy thời tiết cho: '{location}' (Date: {date}, Activity: {activity})")
        real_weather = await fetch_real_weather(location, date=date, activity=activity)
        logger.info(f"[TOOL: WEATHER] Kết quả thật: {real_weather}")
        
        logger.info("[AGENT] Truyền kết quả Thời tiết cho LLM tổng hợp...")
        stream = self.llm_generator.generate_weather_stream(question, real_weather)
        return stream, []

    async def _tool_combined(self, question: str, location: str = None, date: str = "today",
                              activity: str = None, query_arg: str = None,
                              destination: str = None, top_k: int = 5, **kwargs):
        """Gọi song song Weather API + RAG, rồi tổng hợp một câu trả lời"""
        import asyncio
        from fastapi.concurrency import run_in_threadpool

        rag_query = query_arg or question
        logger.info(f"[TOOL: COMBINED] Weather={location}/{date} | RAG='{rag_query[:40]}'")

        # Chạy song song
        weather_task = fetch_real_weather(location or "Việt Nam", date=date, activity=activity)
        retrieval_top_k = 15 if self.reranker else top_k
        rag_task = run_in_threadpool(
            self.retriever.retrieve,
            query=rag_query,
            top_k=retrieval_top_k,
            destination=destination
        )
        real_weather, chunks = await asyncio.gather(weather_task, rag_task)
        logger.info(f"[TOOL: COMBINED] Nhận được weather + {len(chunks)} chunks RAG")

        if self.reranker and chunks:
            chunks = await run_in_threadpool(
                self.reranker.rerank, query=rag_query, candidates=chunks, top_n=top_k
            )

        stream = self.llm_generator.generate_combined_stream(question, real_weather, chunks)
        return stream, chunks


    # ---------------------------------------------------------
    # TIỆN ÍCH
    # ---------------------------------------------------------
    def _parse_tool_call(self, text: str):
        """Hàm bóc tách JSON bằng Regex (hỗ trợ nested JSON)"""
        import re
        import json
        
        # Ưu tiên 1: Bắt JSON trong code block ```json ... ```
        pattern = r"```json\s*(\{.*?\})\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Ưu tiên 2: Dùng thuật toán đếm ngoặc để bắt JSON LỒNG NHAU (Nested JSON)
        # Regex non-greedy (\{.*?\}) sẽ dừng sớm ở dấu } đầu tiên nên không dùng được
        start = text.find('{')
        if start != -1:
            depth = 0
            for i, ch in enumerate(text[start:], start):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        candidate = text[start:i+1]
                        try:
                            data = json.loads(candidate)
                            if "tool" in data:
                                return data
                        except json.JSONDecodeError:
                            pass
                        break
        return None

    # ---------------------------------------------------------
    # RULE-BASED ROUTER (Keyword-based, Bypass LLM hoàn toàn)
    # ---------------------------------------------------------
    _WEATHER_KEYWORDS = {
        "thời tiết", "thoi tiet", "nhiệt độ", "nhiet do", "mưa", "nắng",
        "bão", "sương", "gió", "độ ẩm", "dự báo", "du bao",
        "hôm nay trời", "hom nay troi", "trời hôm", "thời tiết hôm",
        "weather", "forecast", "rain", "sunny", "storm"
    }
    _RAG_KEYWORDS = {
        "có gì", "chơi gì", "đi đâu", "cần biết", "gợi ý", "recommend",
        "địa điểm", "tham quan", "nên đi", "nên ăn", "thắng cảnh",
        "ăn gì", "quán nào", "khách sạn", "homestay", "lưu trú",
        "nổi tiếng", "hot", "check-in", "sưu tầm",
    }

    def _fast_route(self, question: str) -> dict:
        """
        Rule-based router, thay thế hoàn toàn LLM 1.5B.
        Logic:
          Weather + RAG keywords → combined
          Weather keywords only → get_weather
          Mặc định → search_knowledge_base
        """
        q_lower = question.lower()
        has_weather = any(kw in q_lower for kw in self._WEATHER_KEYWORDS)
        has_rag    = any(kw in q_lower for kw in self._RAG_KEYWORDS)

        # Trích xuất location + date + activity (dùng chung cho weather và combined)
        def _extract_weather_params(q):
            analysis = self.retriever.analyzer.analyze(q)
            loc = analysis.get("destination") or "Việt Nam"
            date = "today"
            if any(w in q for w in ("ngày mai", "ngay mai", "tomorrow", "hôm sau")):
                date = "tomorrow"
            elif any(w in q for w in ("ngày kia", "ngay kia", "ngày mốt")):
                date = "day after tomorrow"
            activity = None
            activity_map = {
                "trekking": ["trekking", "leo núi", "leo nui", "đi bộ đường dài"],
                "cắm trại": ["cắm trại", "cam trai", "camping", "lều"],
                "bơi lội": ["bơi", "tắm biển", "tam bien", "lặn"],
                "chụp ảnh": ["chụp ảnh", "chup anh", "photography", "chụp hình"],
                "săn mây": ["săn mây", "san may", "cloud hunting"],
            }
            for act, kws in activity_map.items():
                if any(kw in q for kw in kws):
                    activity = act
                    break
            return loc, date, activity, analysis.get("expanded_query") or q

        if has_weather and has_rag:
            loc, date, activity, query_arg = _extract_weather_params(q_lower)
            logger.info(f"[RULE-ROUTER] COMBINED → location={loc}, date={date}, rag_query='{query_arg[:40]}'")
            return {"tool": "combined", "kwargs": {
                "location": loc, "date": date, "activity": activity, "query_arg": query_arg
            }}

        if has_weather:
            loc, date, activity, _ = _extract_weather_params(q_lower)
            logger.info(f"[RULE-ROUTER] WEATHER → location={loc}, date={date}")
            return {"tool": "get_weather", "kwargs": {"location": loc, "date": date, "activity": activity}}

        # Mặc định: RAG
        analysis = self.retriever.analyzer.analyze(question)
        query_arg = analysis.get("expanded_query") or question
        logger.info(f"[RULE-ROUTER] RAG → query='{query_arg[:50]}'")
        return {"tool": "search_knowledge_base", "kwargs": {"query_arg": query_arg}}

    # ---------------------------------------------------------
    # LUỒNG CHẠY CHÍNH
    # ---------------------------------------------------------
    @observe(name="ViVu_RAG_Pipeline")
    def ask(self, question: str, top_k: int = 5, destination: str = None):
        """Hàm CLI/Testing — RAG đơn giản"""
        retrieval_top_k = 15 if self.reranker else top_k
        chunks = self.retriever.retrieve(query=question, top_k=retrieval_top_k, destination=destination)
        if self.reranker:
            chunks = self.reranker.rerank(query=question, candidates=chunks, top_n=top_k)
        return self.llm_generator.generate_answer(question, chunks), chunks

    @observe(name="ViVu_RAG_Pipeline")
    async def ask_stream(self, question: str, top_k: int = 5, destination: str = None):
        """Pipeline chính: Rule-based Router (không LLM) → Tool → Qwen 1.7B"""

        logger.info(f"[AGENT] Câu hỏi: '{question}'")

        # ROUTING: Thuần rule-based, không gọi LLM
        tool_call = self._fast_route(question)
        tool_name = tool_call.get("tool")
        kwargs    = tool_call.get("kwargs", {})

        logger.info(f"[AGENT] Route → '{tool_name}' | {list(kwargs.keys())}")

        if tool_name in self.tools:
            return await self.tools[tool_name](
                question=question,
                destination=destination,
                top_k=top_k,
                **kwargs
            )

        # Fallback an toàn
        logger.error(f"[AGENT] Tool '{tool_name}' không tồn tại!")
        return self.llm_generator.generate_direct_stream("Xin lỗi, tôi chưa hiểu câu hỏi này."), []
