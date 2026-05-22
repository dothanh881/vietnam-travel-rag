import time
import json
from langfuse import observe
from fastapi.concurrency import run_in_threadpool
from core.logger import get_logger
from core.tools_exec import fetch_real_weather
from core.tools_exec_budget import estimate_budget
from core.tool_formatters import format_budget_text, format_weather_text
from core.llm_router import LLMRouter
from core.react_agent import ReActAgent

logger = get_logger(__name__)

class TravelRAGPipeline:
    def __init__(self, retriever, llm_generator, reranker=None):
        self.retriever = retriever
        self.llm_generator = llm_generator
        self.reranker = reranker
        self.llm_router = LLMRouter()
        self.react_agent = ReActAgent()
        
        self.tools = {
            "search_knowledge_base": self._tool_search_kb,
            "get_weather": self._tool_get_weather,
            "combined": self._tool_combined,
            "combined_weather_rag": self._tool_combined,
            "plan_itinerary": self._tool_plan_itinerary,
            "plan_full_trip": self._tool_plan_full_trip,
            "estimate_budget": self._tool_estimate_budget,
        }

    # ---------------------------------------------------------
    # ĐỊNH NGHĨA CÁC HÀM THỰC THI TOOL (TÁCH BIỆT LOGIC)
    # ---------------------------------------------------------
    async def _tool_search_kb(self, query_arg: str = None, question: str = None, destination: str = None, top_k: int = 5, **kwargs):
        """Thực thi nghiệp vụ RAG: Tìm kiếm Vector DB và sinh câu trả lời"""
        # Tránh lỗi thiếu query_arg nếu LLM không trả về
        query_arg = query_arg or question

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
        
        weather_text = format_weather_text(json.loads(real_weather))
        
        logger.info("[AGENT] Truyền kết quả Thời tiết cho LLM tổng hợp...")
        stream = self.llm_generator.generate_weather_stream(question, weather_text)
        return stream, [], {"type": "weather", "data": json.loads(real_weather)}

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
            
        weather_text = format_weather_text(json.loads(real_weather))

        stream = self.llm_generator.generate_combined_stream(question, weather_text, chunks)
        return stream, chunks, {"type": "weather", "data": json.loads(real_weather)}


    async def _tool_plan_itinerary(self, question: str, location: str = None,
                                    num_days: int = 3, travel_style: str = "mid",
                                    num_people: int = 1, destination: str = None,
                                    top_k: int = 5, **kwargs):
        """Lập lịch trình du lịch dựa trên RAG context"""
        import asyncio
        dest = location or destination or "Việt Nam"
        rag_query = f"lịch trình du lịch {dest} {num_days} ngày địa điểm tham quan ăn uống"
        logger.info(f"[TOOL: ITINERARY] Lập lịch {num_days} ngày tại {dest}")

        retrieval_top_k = 15 if self.reranker else top_k
        chunks = await run_in_threadpool(
            self.retriever.retrieve, query=rag_query,
            top_k=retrieval_top_k, destination=dest
        )
        if self.reranker and chunks:
            chunks = await run_in_threadpool(
                self.reranker.rerank, query=rag_query,
                candidates=chunks, top_n=top_k
            )

        stream = self.llm_generator.generate_itinerary_stream(
            question=question, chunks=chunks,
            destination=dest, num_days=num_days,
            travel_style=travel_style, num_people=num_people
        )
        return stream, chunks

    async def _tool_plan_full_trip(self, question: str, location: str = None,
                                    num_days: int = 3, travel_style: str = "mid",
                                    num_people: int = 1, destination: str = None,
                                    top_k: int = 5, **kwargs):
        """Lập lịch trình + thời tiết song song (full trip planning)"""
        import asyncio
        dest = location or destination or "Việt Nam"
        rag_query = f"lịch trình du lịch {dest} {num_days} ngày địa điểm tham quan ăn uống"
        logger.info(f"[TOOL: FULL_TRIP] {num_days} ngày tại {dest} ({num_people} người, {travel_style})")

        retrieval_top_k = 15 if self.reranker else top_k
        weather_task = fetch_real_weather(dest, date="today")
        rag_task = run_in_threadpool(
            self.retriever.retrieve, query=rag_query,
            top_k=retrieval_top_k, destination=dest
        )
        real_weather, chunks = await asyncio.gather(weather_task, rag_task)

        if self.reranker and chunks:
            chunks = await run_in_threadpool(
                self.reranker.rerank, query=rag_query,
                candidates=chunks, top_n=top_k
            )

        stream = self.llm_generator.generate_full_trip_stream(
            question=question, chunks=chunks,
            destination=dest, num_days=num_days,
            travel_style=travel_style, num_people=num_people,
            weather_info=real_weather
        )
        return stream, chunks

    async def _tool_estimate_budget(self, question: str, location: str = None,
                                     num_days: int = 3, num_people: int = 1,
                                     travel_style: str = "mid", destination: str = None,
                                     **kwargs):
        """Ước tính ngân sách chuyến đi và giải thích thân thiện."""
        dest = location or destination or "Việt Nam"
        style = travel_style or "mid"
        logger.info(f"[TOOL: BUDGET] {dest} | {num_days}N | {num_people} người | {style}")

        budget = estimate_budget(
            destination=dest,
            num_days=num_days,
            num_people=num_people,
            travel_style=style
        )
        budget_text = format_budget_text(budget)

        stream = self.llm_generator.generate_budget_stream(
            question=question,
            budget_json=budget_text,
            travel_style=style
        )
        # Trả về budget dict trong metadata để routes.py emit chart event
        return stream, [], {"type": "budget_chart", "data": budget}



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
        # Câu hỏi phù hợp/khuyến nghị kép
        "phù hợp", "có nên", "nên không", "có thể", "ra ngoài",
        "ngoài trời", "hoạt động", "đi chơi", "vui chơi",
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
    async def ask_stream(self, question: str, top_k: int = 5, destination: str = None, history: list = None):
        """Pipeline chính: ReAct Agent/LLM Router → Tool(s) song song → LLM tổng hợp"""
        import asyncio

        logger.info(f"[AGENT] Câu hỏi: '{question}'")

        # ROUTING: Dùng ReAct Agent với History (ưu tiên) -> Fallback Rule-based
        try:
            react_out = await self.react_agent.run(question, history)
            action = react_out.get("action", "search_knowledge_base")
            action_input = react_out.get("action_input", {})
            logger.info(f"[AGENT] ReActAgent -> {action} | {list(action_input.keys())}")
            
            if action == "ask_user":
                stream = self.llm_generator.generate_direct_stream(action_input.get("question", "Xin lỗi, tôi cần thêm thông tin. Bạn có thể nói rõ hơn không?"))
                return stream, []
            elif action == "finish":
                stream = self.llm_generator.generate_direct_stream(action_input.get("answer", "Tôi đã tổng hợp thông tin xong."))
                return stream, []
            else:
                tool_names = [action]
                kwargs = action_input
                
        except Exception as e:
            logger.error(f"[AGENT] ReActAgent thất bại: {e}. Fallback to Rule-based.")
            fb = self._fast_route(question)
            tool_names = [fb.get("tool", "search_knowledge_base")]
            kwargs = fb.get("kwargs", {})

        logger.info(f"[AGENT] Thực thi Tool -> {tool_names} | {list(kwargs.keys())}")

        # ── Single tool (luồng hiện tại) ──────────────────────────
        if len(tool_names) == 1:
            tool_name = tool_names[0]
            if tool_name in self.tools:
                return await self.tools[tool_name](
                    question=question, destination=destination, top_k=top_k, **kwargs
                )
            logger.error(f"[AGENT] Tool '{tool_name}' không tồn tại!")
            return self.llm_generator.generate_direct_stream("Xin lỗi, tôi chưa hiểu câu hỏi này."), []

        # ── Multi-tool: chạy song song, merge kết quả ─────────────
        logger.info(f"[AGENT] MULTI-TOOL: chạy song song {tool_names}")
        tasks = []
        for tname in tool_names:
            if tname in self.tools:
                tasks.append(self.tools[tname](
                    question=question, destination=destination, top_k=top_k, **kwargs
                ))
        if not tasks:
            return self.llm_generator.generate_direct_stream("Xin lỗi, tôi chưa hiểu câu hỏi này."), []

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Gộp chunks và metadata từ tất cả tools
        all_chunks = []
        all_metadata = {}
        tool_contexts = {}  # {tool_name: data} để truyền vào LLM

        for tname, result in zip(tool_names, results):
            if isinstance(result, Exception):
                logger.warning(f"[MULTI-TOOL] {tname} thất bại: {result}")
                continue
            if len(result) == 3:
                _, chunks, meta = result
                if meta:
                    all_metadata.update(meta)
                    tool_contexts[tname] = meta.get("data")
            else:
                _, chunks = result[:2]
            if chunks:
                all_chunks.extend(chunks)

        # Tổng hợp câu trả lời kết hợp
        stream = self.llm_generator.generate_multi_tool_stream(
            question=question,
            chunks=all_chunks,
            tool_contexts=tool_contexts,
            tool_names=tool_names
        )

        # Nếu có metadata (VD: budget_chart), trả về 3-tuple
        if all_metadata:
            return stream, all_chunks, all_metadata
        return stream, all_chunks
