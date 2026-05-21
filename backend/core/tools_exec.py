import httpx
import json
from datetime import datetime, timedelta
from core.logger import get_logger
from core.travel_reasoning import translate_weather_desc, TravelReasoner

logger = get_logger(__name__)

def resolve_date(date_label: str) -> str:
    """Chuyển nhãn ngày (today/tomorrow/ngày mai...) thành chuỗi YYYY-MM-DD thực tế."""
    import pytz
    tz_vn = pytz.timezone("Asia/Ho_Chi_Minh")
    today = datetime.now(tz_vn).date()
    
    label = (date_label or "today").lower().strip()
    if label in ("today", "hôm nay", "hom nay", "ngay hom nay"):
        return str(today)
    elif label in ("tomorrow", "ngày mai", "ngay mai", "mai"):
        return str(today + timedelta(days=1))
    elif label in ("day after tomorrow", "ngày kia", "ngay kia"):
        return str(today + timedelta(days=2))
    # Nếu đã là YYYY-MM-DD rồi thì giữ nguyên
    return label

async def fetch_real_weather(location: str, date: str = "today", activity: str = None) -> str:
    """Gọi API wttr.in để lấy thời tiết thật, kèm dự báo và phân tích du lịch (JSON)"""
    target_date_str = resolve_date(date)  # Resolve "tomorrow" -> "2026-05-18"
    url = f"https://wttr.in/{location}?format=j1&lang=vi"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            
            if response.status_code == 200:
                data = response.json()
                
                # 1. Lấy thời tiết hiện tại
                current = data.get("current_condition", [])[0]
                nhiet_do = int(current.get("temp_C", 0))
                mo_ta = current.get("lang_vi", [{"value": ""}])[0].get("value", "")
                if not mo_ta:
                    mo_ta = current.get("weatherDesc", [{"value": ""}])[0].get("value", "")
                
                # Dịch thuật tiếng Anh (nếu API rò rỉ) sang Tiếng Việt
                mo_ta = translate_weather_desc(mo_ta)
                
                current_weather_dict = {
                    "temp_C": nhiet_do,
                    "condition": mo_ta,
                    "humidity": current.get("humidity", "N/A"),
                    "wind_kmph": current.get("windspeedKmph", "N/A")
                }
                
                # 2. Lấy dự báo thời tiết 3 ngày tới
                forecast_list = []
                forecasts = data.get("weather", [])
                for day in forecasts:
                    day_date = day.get("date", "")
                    max_t = day.get("maxtempC", "")
                    min_t = day.get("mintempC", "")
                    
                    hourly = day.get("hourly", [])
                    day_desc = "Không rõ"
                    if len(hourly) > 4:
                        midday = hourly[4]
                        day_desc = midday.get("lang_vi", [{"value": ""}])[0].get("value", "")
                        if not day_desc:
                            day_desc = midday.get("weatherDesc", [{"value": ""}])[0].get("value", "")
                    
                    day_desc = translate_weather_desc(day_desc)
                    forecast_list.append({
                        "date": day_date,
                        "min_temp_C": min_t,
                        "max_temp_C": max_t,
                        "condition": day_desc
                    })
                    
                # 3. Chọn thời tiết đúng ngày để Reasoning
                # Nếu user hỏi ngày mai, reasoning phải dựa vào dự báo ngày mai chứ không phải hiện tại
                reason_temp = nhiet_do
                reason_desc = mo_ta
                target_forecast = next((f for f in forecast_list if f["date"] == target_date_str), None)
                if target_forecast:
                    reason_desc = target_forecast["condition"]
                    reason_temp = int(target_forecast.get("max_temp_C", nhiet_do))
                
                reasoning = TravelReasoner.evaluate_weather_for_activity(reason_desc, reason_temp, activity)
                
                final_output = {
                    "location": location,
                    "requested_date": target_date_str,
                    "requested_activity": activity if activity else "Không xác định",
                    "current_weather": current_weather_dict,
                    "focus_forecast": target_forecast if target_forecast else forecast_list[0] if forecast_list else {},
                    "all_forecast": forecast_list,
                    "travel_suitability": reasoning["suitability"],
                    "warnings": reasoning["warnings"],
                    "tips": reasoning["tips"]
                }
                
                return json.dumps(final_output, ensure_ascii=False, indent=2)
            else:
                logger.error(f"[TOOL EXEC] Lỗi gọi API thời tiết: HTTP {response.status_code}")
                return json.dumps({"error": f"Xin lỗi, ViVu không thể lấy dữ liệu thời tiết của {location} lúc này."}, ensure_ascii=False)
                
    except Exception as e:
        logger.error(f"[TOOL EXEC] Lỗi kết nối mạng: {e}")
        return json.dumps({"error": "Hệ thống dự báo thời tiết đang bảo trì, bạn thông cảm nhé."}, ensure_ascii=False)
