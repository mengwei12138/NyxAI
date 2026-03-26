"""
Bot API 客户端 - 调用 Backend API (Bot 专用接口)
"""
import requests
import base64
from typing import Optional, Dict, Any, Tuple

# 导入 Bot 配置（确保 .env 已加载）
from bot.config import BACKEND_URL


class BotAPIClient:
    """Bot 专用 API 客户端 - 使用 /api/bot/ 前缀的接口"""

    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.telegram_id = None

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """发送 HTTP 请求"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, timeout=60, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API 请求失败: {e}")
            raise

    def set_telegram_id(self, telegram_id: int):
        """设置当前用户的 telegram_id"""
        self.telegram_id = telegram_id

    # ========== Bot 认证相关 ==========

    def bot_auth(self, telegram_id: int, first_name: str, username: str = None) -> Dict:
        """Bot 认证：注册或登录"""
        self.telegram_id = telegram_id
        return self._request(
            "POST",
            "/api/bot/auth",
            params={
                "telegram_id": telegram_id,
                "first_name": first_name,
                "username": username
            }
        )

    def get_me(self) -> Dict:
        """获取当前用户信息"""
        return self._request(
            "GET", "/api/bot/me",
            params={"telegram_id": self.telegram_id}
        )

    # ========== 角色相关 ==========

    def get_roles(self, mode: str = "public") -> list:
        """获取角色列表"""
        try:
            result = self._request(
                "GET", "/api/bot/roles",
                params={"telegram_id": self.telegram_id, "mode": mode}
            )
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"获取角色列表失败: {e}")
            return []

    def get_role(self, role_id: int) -> Optional[Dict]:
        """获取角色详情"""
        try:
            return self._request(
                "GET", f"/api/bot/roles/{role_id}",
                params={"telegram_id": self.telegram_id}
            )
        except Exception as e:
            print(f"获取角色详情失败: {e}")
            return None

    # ========== 聊天相关 ==========

    def send_message(self, role_id: int, message: str) -> Optional[Dict]:
        """发送消息并获取 AI 回复"""
        try:
            return self._request(
                "POST", f"/api/bot/chat/{role_id}",
                params={"telegram_id": self.telegram_id, "message": message}
            )
        except Exception as e:
            print(f"发送消息失败: {e}")
            return None

    def get_chat_history(self, role_id: int, limit: int = 20) -> list:
        """获取聊天历史"""
        try:
            return self._request(
                "GET", f"/api/bot/chat/history/{role_id}",
                params={"telegram_id": self.telegram_id, "limit": limit}
            )
        except:
            return []

    def clear_chat_history(self, role_id: int) -> bool:
        """清空聊天历史"""
        try:
            self._request(
                "DELETE", f"/api/bot/chat/history/{role_id}",
                params={"telegram_id": self.telegram_id}
            )
            return True
        except:
            return False

    # ========== TTS 相关 ==========

    def generate_tts(self, text: str, role_id: int = None) -> Optional[Dict]:
        """生成 TTS 语音"""
        try:
            result = self._request(
                "POST", "/api/bot/tts",
                params={
                    "telegram_id": self.telegram_id,
                    "text": text,
                    "role_id": role_id
                }
            )
            if result.get("success") and result.get("audio"):
                # 解码 base64 音频数据
                audio_data = base64.b64decode(result["audio"])
                return {
                    "success": True,
                    "audio_data": audio_data,
                    "format": result.get("format", "mp3")
                }
            return result
        except Exception as e:
            print(f"生成 TTS 失败: {e}")
            return {"success": False, "error": str(e)}

    # ========== 文生图相关 ==========

    def generate_image(self, role_id: int, chat_history: str) -> Optional[str]:
        """生成图片"""
        try:
            result = self._request(
                "POST", "/api/bot/image/generate",
                params={
                    "telegram_id": self.telegram_id,
                    "role_id": role_id,
                    "chat_history": chat_history
                }
            )
            return result.get("task_id")
        except Exception as e:
            print(f"生成图片失败: {e}")
            return None

    def get_image_status(self, task_id: str) -> Optional[Dict]:
        """获取图片生成状态"""
        try:
            return self._request(
                "GET", f"/api/bot/image/status/{task_id}",
                params={"telegram_id": self.telegram_id}
            )
        except Exception as e:
            print(f"获取图片状态失败: {e}")
            return None

    def save_image(self, message_id: int, image_url: str) -> bool:
        """将生成的图片 URL 写入聊天消息（使 Web 端可见）"""
        try:
            self._request(
                "POST", "/api/bot/image/save",
                params={
                    "telegram_id": self.telegram_id,
                    "message_id": message_id,
                    "image_url": image_url
                }
            )
            return True
        except Exception as e:
            print(f"保存图片 URL 失败: {e}")
            return False

    def get_role_states(self, role_id: int) -> Optional[Dict]:
        """获取用户对角色的状态（用户隔离）"""
        try:
            result = self._request(
                "GET", f"/api/bot/states/{role_id}",
                params={"telegram_id": self.telegram_id}
            )
            return result.get("states", {}) if result else {}
        except Exception as e:
            print(f"获取角色状态失败: {e}")
            return {}

    def reset_role_states(self, role_id: int) -> bool:
        """重置用户对角色的状态为默认值"""
        try:
            self._request(
                "POST", f"/api/bot/reset-states/{role_id}",
                params={"telegram_id": self.telegram_id}
            )
            return True
        except Exception as e:
            print(f"重置角色状态失败: {e}")
            return False


# 全局客户端实例
api_client = BotAPIClient()
