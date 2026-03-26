"""
AI 服务模块
整合 Agent、Engine、API Client 功能
"""
import json
import re
import copy
import asyncio
import httpx
from typing import List, Dict, Optional, Tuple, AsyncGenerator
from sqlmodel import Session, select
from app.database import engine
from app.models import Role, RoleState, ChatMessage
from app.config import get_settings
from app.utils.prompts import get_roleplay_system_prompt, get_roleplay_system_fallback_prompt, get_roleplay_story_prompt

settings = get_settings()


class APIError(Exception):
    """API 调用错误"""
    pass


class AIChatService:
    """AI 聊天服务"""

    @staticmethod
    def get_agent_profile(role_id: int, user_id: int = None) -> Tuple[Dict, Dict]:
        """
        从数据库中读取智能体的配置和状态

        Args:
            role_id: 角色ID
            user_id: 用户ID（如果提供，返回用户隔离的状态）

        Returns:
            (profile, states) - 角色配置和状态字典
        """
        with Session(engine) as session:
            # 获取角色基本信息
            role = session.get(Role, role_id)
            if not role:
                raise ValueError(f"角色不存在: {role_id}")

            # 获取状态配置
            states_rows = session.exec(
                select(RoleState).where(RoleState.role_id == role_id)
            ).all()

            # 构建 profile
            profile = {
                "name": role.name,
                "persona": role.persona,
                "scenario": role.scenario or "",
                "user_persona": role.user_persona or "你是我的主人",
                "appearance_tags": role.appearance_tags or "",
                "image_style": role.image_style or "anime",
                "greeting": role.greeting or f"你好，我是{role.name}。让我们开始对话吧！",
                "storyline": role.storyline or "",
                "plot_milestones": role.plot_milestones or "",
            }

            # 构建状态字典
            states = {}

            if user_id:
                # 获取用户隔离的状态
                from app.models import UserRoleState
                user_states = session.exec(
                    select(UserRoleState).where(
                        UserRoleState.user_id == user_id,
                        UserRoleState.role_id == role_id
                    )
                ).all()
                user_state_map = {
                    s.state_name: s.state_value for s in user_states}

                for state in states_rows:
                    # 优先使用用户自定义值，否则使用默认值
                    state_value = user_state_map.get(
                        state.state_name, state.default_value)
                    states[state.state_name] = {
                        "value": state_value,
                        "desc": state.description or ""
                    }
            else:
                # 使用默认状态
                for state in states_rows:
                    states[state.state_name] = {
                        "value": state.current_value or state.default_value,
                        "desc": state.description or ""
                    }

            return profile, states

    @staticmethod
    def build_system_prompt(profile: Dict, states: Dict, story_mode: bool = False) -> str:
        """
        构建角色扮演系统提示词
        """
        # 加载提示词模板：剧情模式使用专用模板
        try:
            if story_mode:
                template = get_roleplay_story_prompt()
            else:
                template = get_roleplay_system_prompt()
        except Exception as e:
            print(f"[AI] 加载提示词失败: {e}")
            template = AIChatService._get_default_system_prompt()

        current_state_str = json.dumps(
            {k: v["value"] for k, v in states.items()}, ensure_ascii=False)
        state_rules_str = json.dumps(
            {k: {"desc": v["desc"]} for k, v in states.items()}, ensure_ascii=False)

        fmt_kwargs = dict(
            name=profile.get('name', ''),
            persona=profile.get('persona', ''),
            scenario=profile.get('scenario', ''),
            user_persona=profile.get('user_persona', ''),
            current_states=current_state_str,
            state_rules=state_rules_str,
        )

        # 剧情模式额外参数：大纲 + 关键节点
        if story_mode:
            milestones_raw = profile.get('plot_milestones', '') or ''
            if milestones_raw:
                try:
                    milestones = json.loads(milestones_raw)
                    lines = [
                        f"{i+1}. {m.get('title', '')}: {m.get('description', '')}"
                        for i, m in enumerate(milestones)
                    ]
                    plot_milestones_text = "\n".join(lines)
                except Exception:
                    plot_milestones_text = milestones_raw
            else:
                plot_milestones_text = "（未设置）"

            fmt_kwargs['storyline'] = profile.get('storyline', '') or '（未设置）'
            fmt_kwargs['plot_milestones_text'] = plot_milestones_text

        result = template.format(**fmt_kwargs)

        # 动态追加：用实际 state key 替换 prompt 末尾的 JSON 示例
        # 确保 AI 明确知道要输出哪些 key（避免输出固定的 affection/arousal）
        if states:
            state_example = {k: v["value"] for k, v in states.items()}
            state_example_str = json.dumps(
                state_example, ensure_ascii=False, indent=2)
            state_keys_str = '、'.join(f'"{k}"' for k in states.keys())
            result += (
                f"\n\n## MANDATORY STATE UPDATE\n"
                f"You MUST end EVERY response with this EXACT JSON block (update values based on context):\n"
                f"```json\n{state_example_str}\n```\n"
                f"The keys MUST be exactly: {state_keys_str}. DO NOT omit this block."
            )

        return result

    @staticmethod
    def _get_default_system_prompt() -> str:
        """默认系统提示词模板（从 prompts 文件加载，避免硬编码）"""
        try:
            return get_roleplay_system_fallback_prompt()
        except Exception as e:
            print(f"[AI] 加载 fallback 提示词失败: {e}")
            # 最后一层备用：内嵌简化版本
            return (
                "You are a character in an immersive roleplay. "
                "Name: {name}. Persona: {persona}. Scenario: {scenario}. User: {user_persona}.\n"
                "Current States: {current_states}\nState Rules: {state_rules}\n"
                "Reply with roleplay text followed by JSON state update."
            )

    @staticmethod
    def build_messages(
        role_id: int,
        user_message: str,
        history: List[ChatMessage],
        profile: Dict,
        states: Dict,
        story_mode: bool = False
    ) -> List[Dict]:
        """
        构建消息列表
        """
        messages = []

        # 添加系统提示词
        system_prompt = AIChatService.build_system_prompt(
            profile, states, story_mode=story_mode)
        messages.append({"role": "system", "content": system_prompt})

        # 添加历史消息（最多10条）
        for msg in history[-10:]:
            role_map = {
                "user": "user",
                "assistant": "assistant",
                "system": "system"
            }
            messages.append({
                "role": role_map.get(msg.role, "user"),
                "content": msg.content
            })

        # 添加当前用户消息
        messages.append({"role": "user", "content": user_message})

        return messages

    @staticmethod
    async def send_chat_request(
        messages: List[Dict],
        max_retries: int = 1,
        timeout: int = 90
    ) -> str:
        """
        发送聊天请求到 AI API（使用 httpx 异步，不阻塞事件循环）
        """
        # 优先使用 OpenRouter，如果没有则使用 OpenAI
        if settings.OPENROUTER_API_KEY:
            api_key = settings.OPENROUTER_API_KEY
            api_url = settings.OPENROUTER_API_URL
        elif settings.OPENAI_API_KEY:
            api_key = settings.OPENAI_API_KEY
            api_url = f"{settings.OPENAI_BASE_URL}/chat/completions"
        else:
            raise APIError(
                "API Key 未配置，请设置 OPENROUTER_API_KEY 或 OPENAI_API_KEY")

        model = settings.MODEL_NAME

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.85,
        }

        # OpenRouter 需要额外的 headers
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://nyx-ai.local",  # OpenRouter 要求
            "X-Title": "Nyx AI"  # OpenRouter 要求
        }

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        api_url,
                        headers=headers,
                        json=payload
                    )

                if response.status_code == 429:
                    raise APIError("API 请求过于频繁")
                elif response.status_code == 401:
                    raise APIError("API Key 无效")
                elif response.status_code == 400:
                    error_detail = response.text
                    print(f"[AI] 400错误详情: {error_detail}")
                    raise APIError(f"请求格式错误: {error_detail[:200]}")

                response.raise_for_status()

                data = response.json()
                if "choices" not in data or not data["choices"]:
                    raise APIError("AI 返回数据格式异常")

                return data["choices"][0]["message"]["content"]

            except httpx.TimeoutException:
                last_error = APIError("请求超时")
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                continue
            except APIError:
                raise
            except Exception as e:
                raise APIError(f"API 调用失败: {str(e)}")

        if last_error:
            raise last_error
        raise APIError("API 调用失败")

    @staticmethod
    async def send_chat_request_stream(
        messages: List[Dict],
        timeout: int = 90
    ) -> AsyncGenerator[str, None]:
        """
        流式发送聊天请求，逐块 yield token
        """
        if settings.OPENROUTER_API_KEY:
            api_key = settings.OPENROUTER_API_KEY
            api_url = settings.OPENROUTER_API_URL
        elif settings.OPENAI_API_KEY:
            api_key = settings.OPENAI_API_KEY
            api_url = f"{settings.OPENAI_BASE_URL}/chat/completions"
        else:
            raise APIError("API Key 未配置")

        payload = {
            "model": settings.MODEL_NAME,
            "messages": messages,
            "temperature": 0.85,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://nyx-ai.local",
            "X-Title": "Nyx AI"
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", api_url, headers=headers, json=payload) as response:
                if response.status_code == 429:
                    raise APIError("API 请求过于频繁")
                elif response.status_code == 401:
                    raise APIError("API Key 无效")
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            yield token
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    @staticmethod
    def extract_and_update_states(
        ai_reply: str,
        current_states: Dict
    ) -> Tuple[str, bool]:
        """
        解析 AI 回复中的 JSON，更新状态

        Returns:
            (clean_text, is_updated)
        """
        clean_text = ai_reply

        def _apply_new_states(new_states: dict) -> bool:
            """
            将 AI 解析出的状态更新合并到 current_states。
            clothing_state 是系统级追踪字段，即便角色未定义该 RoleState
            也强制写入，确保衣物变化持续追踪。
            """
            updated = False
            for key, val in new_states.items():
                if key in current_states:
                    current_states[key]["value"] = val
                    updated = True
                elif key == 'clothing_state':
                    # clothing_state 是系统级字段：即使角色没有定义此 RoleState，
                    # 也强制追加到 current_states，以便后续写入 UserRoleState
                    current_states['clothing_state'] = {
                        "value": val,
                        "desc": "当前衣物状态"
                    }
                    updated = True
            return updated

        # 优先匹配 ```json 代码块
        json_block_match = re.search(
            r'```json\s*(\{[\s\S]*?\})\s*```', ai_reply, re.DOTALL)
        if json_block_match:
            try:
                new_states = json.loads(json_block_match.group(1))
                updated = _apply_new_states(new_states)
                clean_text = ai_reply.replace(
                    json_block_match.group(0), "").strip()
                return clean_text, updated
            except json.JSONDecodeError:
                pass

        # 备用：匹配末尾的 JSON 对象（包含已知状态名 key，支持中英文）
        known_keys = list(current_states.keys()) + \
            ['affection', 'arousal', 'mood', 'clothing_state']
        key_pattern = '|'.join(re.escape(k) for k in known_keys)
        if key_pattern:
            fallback_match = re.search(
                r'(\{[\s\S]*?(?:' + key_pattern + r')[\s\S]*?\})\s*$', ai_reply)
        else:
            fallback_match = re.search(
                r'(\{[\s\S]*"(affection|arousal|mood|clothing_state)"[\s\S]*\})\s*$', ai_reply)
        if fallback_match:
            try:
                new_states = json.loads(fallback_match.group(1))
                updated = _apply_new_states(new_states)
                clean_text = ai_reply.replace(
                    fallback_match.group(0), "").strip()
                return clean_text, updated
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        return clean_text, False

    @staticmethod
    def extract_story_choices(ai_reply: str) -> Tuple[str, List[str]]:
        """
        从 AI 回复中提取剧情选项，返回 (去掉选项块后的纯文本, 选项列表)
        选项列表示例：["我说...", "我转身...", "我沉默..."]
        若无匹配则返回 (原文本, [])
        """
        pattern = r'```choices\s*([\s\S]*?)```'
        match = re.search(pattern, ai_reply)
        if not match:
            return ai_reply, []
        block = match.group(1).strip()
        choices = []
        for line in block.splitlines():
            line = line.strip()
            m = re.match(r'^[A-Ca-c][.．、]\s*(.+)', line)
            if m:
                choices.append(m.group(1).strip())
        clean_text = ai_reply[:match.start()].strip()
        return clean_text, choices

    @staticmethod
    async def chat(
        role_id: int,
        user_id: int,
        message: str,
        history: List[ChatMessage],
        story_mode: bool = False
    ) -> Dict:
        """
        主聊天方法

        Returns:
            {
                "content": AI回复内容,
                "states": 更新后的状态,
                "image_url": 生成的图片URL（可选）
            }
        """
        # 1. 获取角色配置（使用用户隔离的状态）
        profile, states = AIChatService.get_agent_profile(role_id, user_id)

        # 2. 构建消息
        messages = AIChatService.build_messages(
            role_id, message, history, profile, states, story_mode=story_mode
        )

        # 3. 发送请求
        ai_reply = await AIChatService.send_chat_request(messages)

        # 4. 提取并更新状态
        clean_text, states_updated = AIChatService.extract_and_update_states(
            ai_reply, states
        )

        # 4b. 若剧情模式，提取选项
        story_choices: List[str] = []
        if story_mode:
            clean_text, story_choices = AIChatService.extract_story_choices(
                clean_text)

        # 5. 更新用户隔离的状态
        if states_updated:
            from app.services import ChatService
            with Session(engine) as session:
                for state_name, state_data in states.items():
                    # 保存到用户角色状态表（用户隔离）
                    await ChatService.update_user_role_state(
                        session, user_id, role_id,
                        state_name, str(state_data["value"])
                    )

        return {
            "content": clean_text,
            "states": states,
            # image_url 由调用方在文生图任务完成后通过 /bot/image/save 或
            # /chat/save-image/{message_id} 写回消息记录，此处聊天流程本身不触发文生图
            "image_url": None,
            "choices": story_choices
        }
