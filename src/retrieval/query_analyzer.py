
class TravelQueryAnalyzer:
    """
    Phân tích query cho travel domain:
    - intent: food | place | itinerary | general
    - destination: Đà Lạt, Phú Quốc...
    """

    def analyze(self, query: str) -> dict:
        q = query.lower()

        # -------- detect intent --------
        intent = "general"

        if any(k in q for k in ["ăn", "món", "đặc sản"]):
            intent = "food"

        elif any(k in q for k in ["đi đâu", "chơi", "tham quan"]):
            intent = "place"

        elif any(k in q for k in ["lịch trình", "plan", "itinerary"]):
            intent = "itinerary"

        # -------- detect destination --------
        destination = None

        if "đà lạt" in q:
            destination = "Đà Lạt"

        elif "phú quốc" in q:
            destination = "Phú Quốc"

        elif "sapa" in q or "sa pa" in q:
            destination = "Sa Pa"

        #  ....... bổ sung

        return {
            "intent": intent,
            "destination": destination
        }