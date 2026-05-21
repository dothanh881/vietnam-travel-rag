import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Từ điển dịch thuật thời tiết toàn diện
WEATHER_VI = {
    "sunny": "Trời nắng",
    "clear": "Trời quang",
    "partly cloudy": "Trời nhiều mây",
    "cloudy": "Nhiều mây",
    "overcast": "Trời âm u",
    "mist": "Có sương mù nhẹ",
    "patchy rain possible": "Có thể có mưa rào",
    "patchy snow possible": "Có thể có tuyết",
    "patchy sleet possible": "Có thể có mưa tuyết",
    "patchy freezing drizzle possible": "Có thể có sương giá",
    "thundery outbreaks possible": "Có thể có dông",
    "blowing snow": "Bão tuyết",
    "blizzard": "Bão tuyết lớn",
    "fog": "Sương mù",
    "freezing fog": "Sương mù lạnh",
    "patchy light drizzle": "Mưa phùn rải rác",
    "light drizzle": "Mưa bay nhẹ",
    "freezing drizzle": "Mưa bụi giá rét",
    "heavy freezing drizzle": "Mưa bụi rét đậm",
    "patchy light rain": "Mưa rào nhẹ rải rác",
    "light rain": "Mưa nhỏ",
    "moderate rain at times": "Thỉnh thoảng mưa vừa",
    "moderate rain": "Mưa vừa",
    "heavy rain at times": "Thỉnh thoảng mưa to",
    "heavy rain": "Mưa to",
    "light freezing rain": "Mưa lạnh nhẹ",
    "moderate or heavy freezing rain": "Mưa lạnh vừa hoặc to",
    "light sleet": "Mưa tuyết nhẹ",
    "moderate or heavy sleet": "Mưa tuyết vừa hoặc to",
    "patchy light snow": "Tuyết nhẹ rải rác",
    "light snow": "Tuyết rơi nhẹ",
    "patchy moderate snow": "Tuyết rơi vừa rải rác",
    "moderate snow": "Tuyết rơi vừa",
    "patchy heavy snow": "Tuyết rơi dày rải rác",
    "heavy snow": "Tuyết rơi dày",
    "ice pellets": "Mưa đá",
    "light rain shower": "Mưa rào nhẹ",
    "moderate or heavy rain shower": "Mưa rào vừa đến to",
    "torrential rain shower": "Mưa rào rất to",
    "light sleet showers": "Mưa tuyết nhẹ",
    "moderate or heavy sleet showers": "Mưa tuyết vừa hoặc to",
    "light snow showers": "Tuyết rơi nhẹ",
    "moderate or heavy snow showers": "Tuyết rơi vừa hoặc to",
    "light showers of ice pellets": "Mưa đá nhẹ",
    "moderate or heavy showers of ice pellets": "Mưa đá vừa hoặc to",
    "patchy light rain with thunder": "Mưa rào nhẹ kèm dông",
    "moderate or heavy rain with thunder": "Mưa vừa hoặc to kèm dông",
    "patchy light snow with thunder": "Tuyết rơi nhẹ kèm dông",
    "moderate or heavy snow with thunder": "Tuyết rơi vừa hoặc to kèm dông",
    "patchy rain nearby": "Có mưa rào rải rác"
}

def translate_weather_desc(desc: str) -> str:
    """Dịch chuỗi thời tiết tiếng Anh sang tiếng Việt"""
    if not desc:
        return "Không rõ"
    
    desc_lower = desc.strip().lower()
    
    # Tìm kiếm trực tiếp
    if desc_lower in WEATHER_VI:
        return WEATHER_VI[desc_lower]
        
    # Tìm kiếm một phần
    for eng, vi in WEATHER_VI.items():
        if eng in desc_lower:
            return vi
            
    return desc # Fallback nếu không có trong từ điển

class TravelReasoner:
    """Chuyên gia lý luận: Chấm điểm thời tiết theo Activity"""
    
    @staticmethod
    def evaluate_weather_for_activity(weather_desc: str, temp: int, activity: str) -> Dict[str, Any]:
        weather_lower = weather_desc.lower()
        
        # Mặc định
        suitability = "Bình thường"
        warnings = []
        tips = []
        
        # Phân loại thời tiết
        is_raining = any(w in weather_lower for w in ["mưa", "rain", "drizzle", "shower", "thunder"])
        is_hot = temp >= 33
        is_cold = temp <= 15
        is_sunny = any(w in weather_lower for w in ["nắng", "quang", "sunny", "clear"])
        is_cloudy = any(w in weather_lower for w in ["mây", "âm u", "cloudy", "overcast"])
        is_foggy = any(w in weather_lower for w in ["sương", "fog", "mist"])
        
        # Không có activity rõ ràng
        if not activity:
            if is_raining:
                suitability = "Cần lưu ý"
                warnings.append("Trời có mưa, các hoạt động ngoài trời sẽ bị hạn chế.")
                tips.append("Ưu tiên tham quan trong nhà (bảo tàng, quán cafe, trung tâm thương mại).")
                tips.append("Luôn mang theo ô hoặc áo mưa dự phòng.")
            elif is_hot:
                suitability = "Cần lưu ý"
                warnings.append("Thời tiết khá nóng bức.")
                tips.append("Uống đủ nước, thoa kem chống nắng và tránh hoạt động lâu ngoài trời vào giữa trưa.")
            elif is_cold:
                suitability = "Cần lưu ý"
                warnings.append("Nhiệt độ khá lạnh.")
                tips.append("Mặc đủ ấm, ưu tiên các món ăn nóng hổi đặc sản địa phương.")
            elif is_sunny:
                suitability = "Lý tưởng"
                tips.append("Thời tiết rất đẹp cho các hoạt động tham quan ngoài trời và chụp ảnh.")
            else:
                suitability = "Phù hợp"
                tips.append("Thời tiết bình thường, có thể tham quan bình thường.")
                
            return {
                "suitability": suitability,
                "warnings": warnings,
                "tips": tips
            }
            
        activity_lower = activity.lower()
        
        # Logic theo Activity
        if "trekking" in activity_lower or "leo núi" in activity_lower or "hiking" in activity_lower:
            if is_raining:
                suitability = "Không phù hợp"
                warnings.append("Trời mưa làm đường rừng núi rất trơn trượt, nguy hiểm cho việc trekking.")
                tips.append("Nên dời lịch trình trekking hoặc chuyển sang các hoạt động an toàn hơn.")
            elif is_hot:
                suitability = "Khá phù hợp"
                warnings.append("Nhiệt độ cao có thể gây mất nước nhanh khi vận động mạnh.")
                tips.append("Nên bắt đầu trekking từ sáng sớm, mang dư lượng nước uống và điện giải.")
            else:
                suitability = "Rất lý tưởng"
                tips.append("Thời tiết đẹp, đường khô ráo, rất thích hợp để leo núi/trekking.")
                
        elif "beach" in activity_lower or "biển" in activity_lower or "bơi" in activity_lower or "lặn" in activity_lower:
            if is_raining:
                suitability = "Không phù hợp"
                warnings.append("Mưa làm nước biển đục và không an toàn để bơi lội.")
            elif is_foggy or is_cloudy:
                suitability = "Bình thường"
                tips.append("Trời nhiều mây, thích hợp đi dạo biển nhưng cảnh chụp ảnh có thể không rực rỡ.")
            else:
                suitability = "Rất lý tưởng"
                tips.append("Nắng đẹp, nước biển trong xanh. Nhớ thoa kem chống nắng thường xuyên nhé.")
                
        elif "camping" in activity_lower or "cắm trại" in activity_lower:
            if is_raining:
                suitability = "Rất xấu"
                warnings.append("Trời mưa sẽ làm hỏng trải nghiệm cắm trại, đất nền ẩm ướt.")
                tips.append("Tuyệt đối nên chuyển sang lưu trú tại Homestay/Khách sạn.")
            elif is_cold:
                suitability = "Tuyệt vời (Cần chuẩn bị)"
                tips.append("Cắm trại thời tiết lạnh rất thú vị. Hãy chuẩn bị túi ngủ cách nhiệt tốt và củi đốt lửa trại.")
            else:
                suitability = "Rất lý tưởng"
                tips.append("Thời tiết hoàn hảo để cắm trại qua đêm và nướng BBQ.")
                
        elif "cloud" in activity_lower or "săn mây" in activity_lower:
            if is_raining:
                suitability = "Không phù hợp"
                warnings.append("Trời mưa thường sẽ làm mây tan hoặc biến thành mù đặc không thấy cảnh.")
            elif is_foggy or is_cloudy:
                suitability = "Rất lý tưởng"
                tips.append("Độ ẩm cao và có sương/mây. Tỷ lệ săn được biển mây thành công là rất cao!")
            elif is_sunny and temp > 25:
                suitability = "Thấp"
                warnings.append("Trời nắng ráo và ấm, khả năng có biển mây không cao.")
                
        elif "photo" in activity_lower or "chụp" in activity_lower or "check-in" in activity_lower:
            if is_raining:
                suitability = "Kém"
                warnings.append("Mưa sẽ gây khó khăn cho việc sử dụng thiết bị máy ảnh và ánh sáng xỉn.")
                tips.append("Nên chụp ảnh tại các quán cafe hoặc kiến trúc trong nhà.")
            elif is_sunny:
                suitability = "Hoàn hảo"
                tips.append("Ánh sáng mặt trời rực rỡ là điều kiện tốt nhất để có những bức ảnh phong cảnh tuyệt đẹp.")
            elif is_cloudy:
                suitability = "Khá ổn"
                tips.append("Ánh sáng dịu nhẹ của trời mây rất tốt để chụp chân dung (portrait) không bị bóng đổ gắt.")
        
        else:
            # Fallback for unrecognized activities
            suitability = "Có thể thực hiện"
            if is_raining:
                warnings.append("Chú ý trời có mưa rào.")
            
        return {
            "suitability": suitability,
            "warnings": warnings,
            "tips": tips
        }
