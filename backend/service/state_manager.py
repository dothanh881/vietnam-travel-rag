import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Lưu tạm State trên RAM thay vì dùng Redis
_IN_MEMORY_STORE: Dict[str, Any] = {}

class TravelStateManager:
    """Quản lý trạng thái (State) bằng RAM (In-Memory) tạm thời."""
    
    def __init__(self):
        self.redis = None
        logger.info("[StateManager] Đang sử dụng RAM (In-Memory) để lưu State (Đã tắt Redis).")

    def get_state(self, session_id: str) -> Dict[str, Any]:
        """Lấy trạng thái luồng chat hiện tại của user, trả về dict."""
        if not session_id:
            return {}
        try:
            state = _IN_MEMORY_STORE.get(session_id, {})
            return state
        except Exception as e:
            logger.error(f"[StateManager] Lỗi khi đọc state với session {session_id}: {e}")
            return {}

    def set_state(self, session_id: str, state: Dict[str, Any], ttl_seconds: int = 3600 * 24):
        """Cập nhật trạng thái luồng chat."""
        if not session_id:
            return False
            
        try:
            _IN_MEMORY_STORE[session_id] = state
            logger.debug(f"[StateManager] Đã update state cho {session_id}: {state}")
            return True
        except Exception as e:
            logger.error(f"[StateManager] Lỗi khi ghi state cho session {session_id}: {e}")
            return False

    def update_context(self, session_id: str, new_destination: Optional[str] = None, topic: Optional[str] = None):
        """Hàm helper cập nhật destination và lưu history"""
        if not session_id:
            return
            
        try:
            current_state = self.get_state(session_id)
            history = current_state.get("history", [])
            active = current_state.get("active")
            current_topic = current_state.get("topic")
            
            needs_update = False

            if new_destination and active != new_destination:
                # Tránh trùng lặp liên tục
                if not history or history[-1] != new_destination:
                    history.append(new_destination)
                    
                # Giữ lịch sử không quá dài (Tối đa 10 địa điểm)
                if len(history) > 10:
                    history = history[-10:]
                    
                current_state["active"] = new_destination
                current_state["history"] = history
                needs_update = True
                
            if topic and current_topic != topic:
                current_state["topic"] = topic
                needs_update = True

            if needs_update:
                self.set_state(session_id, current_state)
        except Exception as e:
            logger.error(f"[StateManager] Lỗi update context: {e}")
