def format_budget_text(budget: dict) -> str:
    """Chuyển đổi dữ liệu JSON ngân sách thành văn bản tự nhiên cho LLM 1.7B dễ đọc."""
    if not budget:
        return "Không có dữ liệu ngân sách."
        
    try:
        dest = budget.get("destination", "Điểm đến")
        days = budget.get("num_days", 0)
        ppl = budget.get("num_people", 1)
        style = budget.get("travel_style", "")
        
        breakdown = budget.get("breakdown_per_person_per_day", {})
        acc = breakdown.get("accommodation", 0)
        food = breakdown.get("food", 0)
        trans = breakdown.get("transport_local", 0)
        ent = breakdown.get("entrance_fee", 0)
        
        total_acc = acc * days * ppl
        total_food = food * days * ppl
        total_trans = trans * days * ppl
        total_ent = ent * days * ppl
        total_misc = breakdown.get("misc", 0) * days * ppl
        
        flight = budget.get("flight_estimate_total", 0)
        total = budget.get("grand_total", 0)
        
        text = (
            f"Thông tin ước tính chi phí du lịch {dest} trong {days} ngày cho {ppl} người (Phong cách: {style}):\n"
            f"- Tổng chi phí dự kiến: {total:,} VNĐ.\n"
        )
        if flight > 0:
            text += f"- Tiền vé máy bay khứ hồi (tổng cộng): {flight:,} VNĐ.\n"
            
        text += (
            f"- Chi tiết phân bổ ngân sách (Tổng cộng cho cả chuyến đi):\n"
            f"  + Khách sạn/Chỗ ở: {total_acc:,} VNĐ\n"
            f"  + Ăn uống: {total_food:,} VNĐ\n"
            f"  + Đi lại tại chỗ: {total_trans:,} VNĐ\n"
            f"  + Vé tham quan: {total_ent:,} VNĐ\n"
            f"  + Chi phí linh tinh (nước, ăn vặt): {total_misc:,} VNĐ\n"
        )
        return text
    except Exception as e:
        return f"Dữ liệu ngân sách bị lỗi: {str(e)}"

def format_weather_text(weather: dict) -> str:
    """Chuyển đổi dữ liệu JSON thời tiết thành văn bản tự nhiên cho LLM 1.7B dễ đọc."""
    if not weather:
        return "Không có dữ liệu thời tiết."
        
    try:
        loc = weather.get("location", "Điểm đến")
        fc = weather.get("focus_forecast", {})
        cond = fc.get("condition", "")
        t_min = fc.get("min_temp_C", "")
        t_max = fc.get("max_temp_C", "")
        
        suit = weather.get("travel_suitability", {})
        is_suitable = "Phù hợp" if suit.get("is_suitable") else "Không phù hợp"
        reason = suit.get("reason", "")
        
        tips = weather.get("tips", [])
        tips_text = ", ".join(tips) if tips else "Không có lưu ý đặc biệt"
        
        text = (
            f"Thời tiết tại {loc}:\n"
            f"- Tình trạng: {cond}, nhiệt độ dao động từ {t_min}°C đến {t_max}°C.\n"
            f"- Mức độ phù hợp đi lại: {is_suitable}. Lý do: {reason}.\n"
            f"- Lời khuyên: {tips_text}."
        )
        return text
    except Exception as e:
        return f"Dữ liệu thời tiết bị lỗi: {str(e)}"
