import json
from core.logger import get_logger

logger = get_logger(__name__)

# =============================================
# BẢNG GIÁ THAM KHẢO THEO TIER (VNĐ/người/ngày)
# Dựa trên giá thực tế thị trường 2025-2026
# =============================================
BUDGET_TIERS = {
    "budget": {
        "label": "Tiết kiệm",
        "accommodation": 200_000,    # Hostel/nhà trọ
        "food": 150_000,             # Quán bình dân
        "transport_local": 80_000,   # Xe buýt/grab thấp
        "entrance_fee": 50_000,      # Vé tham quan trung bình
        "misc": 50_000,              # Mua sắm nhỏ, nước uống
    },
    "mid": {
        "label": "Trung bình",
        "accommodation": 600_000,    # Khách sạn 2-3 sao
        "food": 300_000,             # Nhà hàng trung cấp
        "transport_local": 150_000,  # Grab/thuê xe máy
        "entrance_fee": 100_000,
        "misc": 150_000,
    },
    "luxury": {
        "label": "Cao cấp",
        "accommodation": 2_000_000,  # Resort/khách sạn 4-5 sao
        "food": 800_000,             # Nhà hàng cao cấp
        "transport_local": 400_000,  # Thuê xe riêng
        "entrance_fee": 200_000,
        "misc": 500_000,
    },
}

# Hệ số điều chỉnh theo điểm đến (một số nơi đắt/rẻ hơn trung bình)
DESTINATION_MULTIPLIER = {
    "hà nội": 1.1,
    "hanoi": 1.1,
    "tp hcm": 1.15,
    "hồ chí minh": 1.15,
    "sài gòn": 1.15,
    "đà nẵng": 1.05,
    "da nang": 1.05,
    "phú quốc": 1.3,
    "phu quoc": 1.3,
    "đà lạt": 0.95,
    "da lat": 0.95,
    "hội an": 1.05,
    "hoi an": 1.05,
    "sa pa": 1.0,
    "nha trang": 1.1,
    "hạ long": 1.2,
    "ha long": 1.2,
}

# Ước tính vé máy bay khứ hồi từ HN/HCM (VNĐ/người)
FLIGHT_ESTIMATE = {
    "đà lạt": 1_200_000,
    "phú quốc": 2_000_000,
    "hội an": 1_500_000,
    "đà nẵng": 1_500_000,
    "nha trang": 1_300_000,
    "sa pa": 1_800_000,
    "hạ long": 500_000,   # Gần HN, thường đi xe
    "hà nội": 1_800_000,
    "tp hcm": 1_800_000,
}


def estimate_budget(destination: str, num_days: int, num_people: int = 1,
                    travel_style: str = "mid", include_flight: bool = True,
                    transport_cost_per_person: int = None,
                    additional_entrance_fees: int = 0) -> dict:
    """
    Ước tính ngân sách chuyến đi du lịch Việt Nam.
    Returns dict với breakdown chi tiết và tổng cộng.
    """
    style = travel_style.lower() if travel_style else "mid"
    if style not in BUDGET_TIERS:
        style = "mid"

    tier = BUDGET_TIERS[style]
    dest_lower = destination.lower() if destination else ""

    # Hệ số điều chỉnh theo điểm đến
    multiplier = 1.0
    for key, val in DESTINATION_MULTIPLIER.items():
        if key in dest_lower:
            multiplier = val
            break

    # Tính chi phí hàng ngày (đã nhân hệ số địa điểm)
    daily = {
        "accommodation": int(tier["accommodation"] * multiplier),
        "food": int(tier["food"] * multiplier),
        "transport_local": int(tier["transport_local"] * multiplier),
        "entrance_fee": int(tier["entrance_fee"]),
        "misc": int(tier["misc"]),
    }
    
    # Cộng thêm phụ phí tham quan (nếu có vé combo được agent lấy từ RAG)
    if additional_entrance_fees > 0:
        # Nếu đã có phí cứng, ta cộng thêm vào tổng hoặc thay thế phí mặc định 1 ngày
        # Đơn giản nhất là chia đều cho số ngày để hiển thị breakdown
        daily["entrance_fee"] += (additional_entrance_fees // num_days)

    # Tổng chi phí sinh hoạt (người * ngày * danh mục)
    total_daily = sum(daily.values()) * num_days * num_people

    # Vé máy bay/di chuyển (1 lần khứ hồi * số người)
    flight_cost = 0
    if transport_cost_per_person is not None:
        flight_cost = transport_cost_per_person * num_people
    elif include_flight:
        for key, cost in FLIGHT_ESTIMATE.items():
            if key in dest_lower:
                flight_cost = cost * num_people
                break
        if not flight_cost:
            flight_cost = 1_500_000 * num_people  # Default nếu không tìm thấy

    total = total_daily + flight_cost

    # Buffer dự phòng 10%
    buffer = int(total * 0.10)

    result = {
        "destination": destination,
        "num_days": num_days,
        "num_people": num_people,
        "travel_style": tier["label"],
        "breakdown_per_person_per_day": daily,
        "flight_estimate_total": flight_cost,
        "subtotal": total_daily,
        "buffer_10pct": buffer,
        "grand_total": total + buffer,
        "grand_total_per_person": (total + buffer) // num_people,
        "currency": "VNĐ",
    }

    logger.info(f"[BUDGET] {destination} | {num_days}N{num_people}P | {style} | Total: {result['grand_total']:,}")
    return result


def format_budget_for_llm(budget: dict) -> str:
    """Chuyển budget dict thành string để truyền vào LLM prompt."""
    return json.dumps(budget, ensure_ascii=False, indent=2)
