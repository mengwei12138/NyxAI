"""
LLM 公共服务层
封装对 OpenRouter / OpenAI 的 HTTP 调用，消除各接口重复代码
"""
import httpx
from typing import List, Dict, Any, Optional
from app.config import get_settings

settings = get_settings()


class LLMError(Exception):
    """LLM 调用错误"""
    pass


class LLMService:
    """LLM 调用公共服务"""

    @staticmethod
    def _get_api_key_and_url() -> tuple[str, str]:
        """获取 API Key 和请求 URL"""
        if settings.OPENROUTER_API_KEY:
            return settings.OPENROUTER_API_KEY, settings.OPENROUTER_API_URL
        elif settings.OPENAI_API_KEY:
            return settings.OPENAI_API_KEY, f"{settings.OPENAI_BASE_URL}/chat/completions"
        raise LLMError("LLM 服务未配置，请设置 OPENROUTER_API_KEY 或 OPENAI_API_KEY")

    @staticmethod
    async def call(
        messages: List[Dict[str, str]],
        max_tokens: int = 500,
        temperature: float = 0.7,
        model: Optional[str] = None,
        timeout: int = 60,
    ) -> str:
        """
        调用 LLM API，返回纯文本回复内容。

        Args:
            messages:     符合 OpenAI 格式的消息列表 [{"role": ..., "content": ...}]
            max_tokens:   最大输出 token 数
            temperature:  温度参数
            model:        指定模型，默认使用配置中的 MODEL_NAME
            timeout:      请求超时秒数

        Returns:
            str: LLM 回复的纯文本内容

        Raises:
            LLMError: API 调用失败时抛出
        """
        api_key, api_url = LLMService._get_api_key_and_url()

        payload: Dict[str, Any] = {
            "model": model or settings.MODEL_NAME,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://nyx-ai.local",
            "X-Title": "Nyx AI",
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(api_url, headers=headers, json=payload)

            if response.status_code == 401:
                raise LLMError("API Key 无效")
            elif response.status_code == 429:
                raise LLMError("API 请求过于频繁，请稍后重试")
            elif response.status_code == 400:
                raise LLMError(f"请求格式错误: {response.text[:200]}")

            response.raise_for_status()

            data = response.json()
            if "choices" not in data or not data["choices"]:
                raise LLMError("LLM 返回数据格式异常")

            return data["choices"][0]["message"]["content"].strip()

        except LLMError:
            raise
        except httpx.TimeoutException:
            raise LLMError("LLM 请求超时")
        except Exception as e:
            raise LLMError(f"LLM 调用失败: {str(e)}")
