import json
from core.logger import get_logger

logger = get_logger(__name__)

# Bảng giả lập giá trung bình
TRANSPORT_PRICES = {
    "flight": {
        "short": 1500000,
        "medium": 2500000,
        "long": 3500000
    },
    "bus": {
        "short": 200000,
        "medium": 500000,
        "long": 800000
    },
    "train": {
        "short": 300000,
        "medium": 800000,
        "long": 1200000
    }
}

def estimate_distance(from_city: str, to_city: str) -> str:
    """Giả lập hàm tính độ dài quãng đường để chọn giá"""
    from_city = from_city.lower()
    to_city = to_city.lower()
    
    # Rất thô sơ, chỉ để demo logic:
    if ("hà nội" in from_city and "hồ chí minh" in to_city) or ("hồ chí minh" in from_city and "hà nội" in to_city):
        return "long"
    if ("hà nội" in from_city and "phú quốc" in to_city) or ("hồ chí minh" in from_city and "sapa" in to_city):
        return "long"
    if ("hà nội" in from_city and "đà nẵng" in to_city) or ("hồ chí minh" in from_city and "đà nẵng" in to_city):
        return "medium"
    return "short"

def search_transport(from_city: str, to_city: str, transport_type: str = "flight") -> str:
    """
    Tìm kiếm ước lượng giá vé di chuyển.
    transport_type có thể là "flight", "bus", hoặc "train".
    """
    logger.info(f"[TOOL] search_transport: {from_city} -> {to_city} (Type: {transport_type})")
    transport_type = transport_type.lower()
    if transport_type not in TRANSPORT_PRICES:
        transport_type = "flight" # Fallback
        
    dist_cat = estimate_distance(from_city, to_city)
    price = TRANSPORT_PRICES[transport_type].get(dist_cat, 1500000)
    
    # Định dạng output json
    result = {
        "from": from_city,
        "to": to_city,
        "transport_type": transport_type,
        "estimated_price_vnd": price,
        "currency": "VND",
        "note": "Đây là giá ước tính khứ hồi trung bình."
    }
    
    return json.dumps(result, ensure_ascii=False)
