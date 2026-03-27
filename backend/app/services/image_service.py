"""
文生图服务
基于 Z-image API 的异步图像生成
"""
import json
import redis
import requests
import time
import uuid
import os
import hashlib
import threading
from typing import Optional, Dict
from app.config import get_settings
from app.utils.prompts import (
    get_image_generation_config,
    get_scene_analyzer_prompt,
    get_visual_describer_prompt
)
from app.services.oss_service import OssService

settings = get_settings()

# 图片本地缓存目录
IMAGE_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))),
    'cache', 'images'
)
os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)

# 进程内已上传 OSS 的 key 集合，避免重复 HEAD 请求
_oss_uploaded_keys: set = set()


def _upload_image_to_oss(local_path: str, oss_key: str) -> Optional[str]:
    """
    上传本地图片到 OSS（进程内已上传则直接返回 URL，跳过网络请求）。
    返回 OSS URL，失败返回 None。
    """
    if not OssService.is_enabled():
        return None
    if oss_key in _oss_uploaded_keys:
        return OssService.get_public_url(oss_key)
    url = OssService.upload_file(local_path, oss_key)
    if url:
        _oss_uploaded_keys.add(oss_key)
    return url


def _restore_image_from_oss(local_path: str, oss_key: str) -> bool:
    """
    本地图片不存在时，尝试从 OSS 流式下载恢复到本地。
    返回是否成功。
    """
    if not OssService.is_enabled():
        return False
    ok = OssService.download_stream(oss_key, local_path)
    if ok:
        print(f"[Image-OSS] 从 OSS 恢复本地缓存: {oss_key}")
        _oss_uploaded_keys.add(oss_key)
    else:
        print(f"[Image-OSS] OSS 无缓存: {oss_key}")
    return ok


def _download_image(image_url: str) -> Optional[str]:
    """
    下载外部图片到本地 cache/images/，并在 OSS 已启用时同步上传。
    返回优先级：OSS 公网 URL > 本地相对路径，失败返回原 URL。
    本地文件被删时优先从 OSS 恢复，避免重新下载。
    """
    try:
        url_hash = hashlib.md5(image_url.encode()).hexdigest()
        ext = 'jpg'
        for candidate in ('png', 'webp', 'gif'):
            if candidate in image_url.lower():
                ext = candidate
                break
        filename = f"{url_hash}.{ext}"
        local_path = os.path.join(IMAGE_CACHE_DIR, filename)
        oss_key = f"images/{filename}"

        # 本地已存在：直接用进程内缓存集合判断是否需要上传，无需 HEAD 请求
        if os.path.exists(local_path):
            print(f"[Image] 使用图片缓存: {filename}")
            oss_url = _upload_image_to_oss(local_path, oss_key)
            return oss_url if oss_url else f"/cache/images/{filename}"

        # 本地不存在：先尝试从 OSS 恢复（避免重新下载外部图片）
        if _restore_image_from_oss(local_path, oss_key):
            return OssService.get_public_url(oss_key)

        # OSS 也没有：从原始 URL 下载
        resp = requests.get(image_url, timeout=30)
        if resp.status_code == 200:
            with open(local_path, 'wb') as f:
                f.write(resp.content)
            print(f"[Image] 图片已保存到本地: {local_path}")
            oss_url = _upload_image_to_oss(local_path, oss_key)
            return oss_url if oss_url else f"/cache/images/{filename}"
        else:
            print(f"[Image] 下载图片失败: {resp.status_code}")
            return image_url  # fallback: 返回原 URL
    except Exception as e:
        print(f"[Image] 下载图片异常: {e}")
        return image_url  # fallback: 返回原 URL


# Redis 任务存储（支持多 worker）

_redis_client = None


def _get_redis():
    """获取 Redis 客户端（单例）"""
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            _redis_client = redis.from_url(redis_url, decode_responses=True)
            _redis_client.ping()
            print(f"[Image-Redis] 连接成功: {redis_url}")
        except Exception as e:
            print(f"[Image-Redis] 连接失败，回退到内存存储: {e}")
            _redis_client = None
    return _redis_client


# 内存回退存储（仅当 Redis 不可用时）
_image_tasks = {}
_tasks_lock = threading.Lock()

# 任务 TTL（秒）
_TASK_TTL_SECONDS = 3600


def _save_task(task_id: str, task_data: dict):
    """保存任务到 Redis 或内存"""
    task_data["created_at"] = time.time()
    redis_client = _get_redis()
    if redis_client:
        try:
            redis_client.hset("nyx:image_tasks", task_id,
                              json.dumps(task_data))
            redis_client.expire("nyx:image_tasks", _TASK_TTL_SECONDS + 300)
            return
        except Exception as e:
            print(f"[Image-Redis] 保存失败: {e}")
    with _tasks_lock:
        _image_tasks[task_id] = task_data


def _get_task(task_id: str) -> dict | None:
    """获取任务状态"""
    redis_client = _get_redis()
    if redis_client:
        try:
            data = redis_client.hget("nyx:image_tasks", task_id)
            if data:
                return json.loads(data)
        except Exception as e:
            print(f"[Image-Redis] 获取失败: {e}")
    with _tasks_lock:
        return _image_tasks.get(task_id)


def _update_task(task_id: str, updates: dict):
    """更新任务字段"""
    task = _get_task(task_id)
    if task:
        task.update(updates)
        _save_task(task_id, task)


def _delete_task(task_id: str):
    """删除任务"""
    redis_client = _get_redis()
    if redis_client:
        try:
            redis_client.hdel("nyx:image_tasks", task_id)
        except Exception:
            pass
    with _tasks_lock:
        _image_tasks.pop(task_id, None)


def _cleanup_expired_tasks():
    """清理过期任务（Redis 自动过期，仅清理内存）"""
    now = time.time()
    with _tasks_lock:
        expired = [
            tid for tid, task in _image_tasks.items()
            if task.get('status') in ('COMPLETED', 'SUCCEEDED', 'ERROR', 'FAILED')
            and now - task.get('created_at', now) > _TASK_TTL_SECONDS
        ]
        for tid in expired:
            del _image_tasks[tid]
        if expired:
            print(f"[Image] 清理内存过期任务 {len(expired)} 条")


# Z-image API prompt 字符上限
_PROMPT_MAX_CHARS = 1950  # 留 50 字符余量，硬上限 2000


def _truncate_prompt(prompt: str, max_chars: int = _PROMPT_MAX_CHARS) -> str:
    """
    将 prompt 截断到 max_chars 字符以内。
    优先在句子结尾（`. `）处截断，保证语义完整；若找不到则直接硬截。
    """
    if len(prompt) <= max_chars:
        return prompt
    truncated = prompt[:max_chars]
    # 找最后一个句点后跟空格的位置，从那里截断以保证语义完整
    last_dot = truncated.rfind('. ')
    if last_dot > max_chars // 2:  # 截断点不能太靠前
        return truncated[:last_dot + 1]
    return truncated.rstrip(', ')


class ImageGenerationError(Exception):
    """图像生成错误"""
    pass


def _llm_post_with_retry(url: str, headers: dict, payload: dict,
                         timeout: int = 60, max_retries: int = 3) -> requests.Response:
    """
    带重试的 LLM HTTP 请求。
    针对 ConnectionError / RemoteDisconnected / Timeout 自动重试。
    """
    last_err = None
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, headers=headers,
                                 json=payload, timeout=timeout)
            return resp
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            last_err = e
            print(
                f"[Image] LLM请求失败 (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
    raise last_err


class ImageService:
    """文生图服务"""

    @staticmethod
    def analyze_scene(
        chat_history: str,
        appearance_tags: str = "",
        current_clothing: str = "",
        default_scene: str = ""
    ) -> tuple:
        """
        第一步：使用 AI 分析对话，生成精确场景描述并提取衣物状态

        关键要求：
        - 只描述单一场景，避免多人物混乱
        - 精确描述动作和衣物状态，避免污染
        - 基于最新一轮对话内容
        - 参考角色的基础外貌、进入本场景前的衣物状态、默认场景环境

        Args:
            chat_history: 聊天记录（仅最新一轮）
            appearance_tags: 角色外貌特征Tags（固定，用于参考基础外貌）
            current_clothing: 用户当前衣物状态（聊天过程中动态变化）
            default_scene: 角色默认场景/环境（创建时设定）

        Returns:
            (场景描述, 提取的衣物状态)
        """
        api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY
        if not api_key:
            return "a scene with a character", None

        try:
            prompt_template = get_scene_analyzer_prompt()

            # 构建用户提示，依次注入：基础外貌、当前衣物、默认场景
            user_content = f"最新对话内容：\n{chat_history}"
            if appearance_tags:
                user_content += f"\n\n[角色固定外貌特征]（发色、眼睛等基础外貌，不变）: {appearance_tags}"
            if current_clothing:
                user_content += (
                    f"\n\n[进入本场景前的衣物状态]: {current_clothing}"
                    f"\n→ 如对话明确改变了衣物（擕破、脱掉、換上等），以对话内容为准；否则保持此状态。"
                )
            if default_scene:
                user_content += (
                    f"\n\n[角色默认场景/环境]: {default_scene}"
                    f"\n→ 如对话未指明场景变化，以此为环境参考。"
                )

            messages = [
                {"role": "system", "content": prompt_template},
                {"role": "user", "content": user_content}
            ]

            response = _llm_post_with_retry(
                url=settings.OPENROUTER_API_URL or f"{settings.OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://nyx-ai.local",
                    "X-Title": "Nyx AI"
                },
                payload={
                    "model": settings.MODEL_NAME,
                    "messages": messages,
                    "temperature": 0.7
                },
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                scene_description = result["choices"][0]["message"]["content"]
                clothing_state = ImageService.extract_clothing_from_scene(
                    scene_description)
                print(f"[Image] 场景分析结果: {scene_description[:200]}...")
                print(f"[Image] 提取的衣物状态: {clothing_state}")
                return scene_description, clothing_state

        except Exception as e:
            print(f"[Image] 场景分析失败: {e}")

        return "a scene with a character", None

    @staticmethod
    def extract_clothing_from_scene(scene_description: str) -> str:
        """
        从场景描述中提取衣物状态

        Returns:
            衣物状态描述，如果没有找到返回None
        """
        # 查找 CLOTHING STATE 部分
        import re

        # 尝试匹配 "CLOTHING STATE" 或 "衣物状态" 部分
        patterns = [
            r'CLOTHING STATE.*?[:：]\s*\n?(.*?)(?=\n\n|\n[A-Z]|$)',
            r'衣物状态.*?[:：]\s*\n?(.*?)(?=\n\n|\n[A-Z]|$)',
            r'穿着.*?[:：]\s*\n?(.*?)(?=\n\n|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, scene_description,
                              re.DOTALL | re.IGNORECASE)
            if match:
                clothing = match.group(1).strip()
                # 清理列表标记
                clothing = re.sub(r'^[-*•]\s*', '',
                                  clothing, flags=re.MULTILINE)
                # 取第一行非空内容
                lines = [l.strip() for l in clothing.split('\n') if l.strip()]
                if lines:
                    return lines[0]

        # 如果没找到特定标记，尝试从整段描述中提取衣物相关词汇
        clothing_keywords = [
            r'(?:穿着|wearing|dressed in)\s*[:：]?\s*([^,.\n]+)',
            r'(?:衣服|clothing|outfit)\s*[:：]?\s*([^,.\n]+)',
            r'(?:裸体|naked|nude)',
            r'(?:黑丝|black stockings|丝袜)',
            r'(?:包臀裙|tight skirt|pencil skirt)',
            r'(?:女仆装|maid outfit|maid dress)',
        ]

        for pattern in clothing_keywords:
            match = re.search(pattern, scene_description, re.IGNORECASE)
            if match:
                return match.group(0).strip()

        return None

    @staticmethod
    def generate_visual_description(scene_description: str, role_config: Dict) -> str:
        """
        第二步：用自然语言详细描述画面（支持多人场景）

        Args:
            scene_description: 场景分析结果
            role_config: 角色配置（外貌、衣物等）

        Returns:
            自然语言视觉描述
        """
        api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY
        if not api_key:
            return "A girl standing in a room"

        try:
            # 构建角色外貌信息
            appearance = role_config.get('appearance_tags', '')
            clothing = role_config.get('clothing_state', '')

            # 从外部文件加载提示词
            system_prompt = get_visual_describer_prompt()

            user_prompt = f"""Scene Analysis:
{scene_description}

## MANDATORY CHARACTER APPEARANCE (DO NOT CHANGE - use EXACTLY as specified):
{appearance}
These appearance features are FIXED. You MUST reproduce them precisely in your description (hair color, eye color, etc.).

Character Current Clothing: {clothing}

Please describe what should be visible in the generated image. Be specific about all characters, their clothing, poses, and the setting. CRITICAL: The female character's appearance (especially hair color and eye color) must exactly match the Appearance Tags above."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response = _llm_post_with_retry(
                url=settings.OPENROUTER_API_URL or f"{settings.OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://nyx-ai.local",
                    "X-Title": "Nyx AI"
                },
                payload={
                    "model": settings.MODEL_NAME,
                    "messages": messages,
                    "temperature": 0.7
                },
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                visual_desc = result["choices"][0]["message"]["content"]
                print(
                    f"[Image] [步骤2完整视觉描述] ({len(visual_desc)} chars):\n{visual_desc}\n")
                return visual_desc

        except Exception as e:
            print(f"[Image] 生成视觉描述失败: {e}")

        return "A girl standing in a room"

    @staticmethod
    def create_generation_task(chat_history: str, role_config: Dict) -> str:
        """
        创建图像生成任务 - Flux/DiT 两步流程（后台线程异步执行）

        立即注册 task_id 并返回（status=PROCESSING），两步 LLM 流程在后台线程中执行：
        1. 场景分析：自然语言描述场景（支持多人）
        2. 视觉描述：用自然语言详细描述画面（直接作为 prompt 使用）
        完成后提交 Z-image 任务，status 切换为 PENDING

        Returns:
            task_id: 任务ID（立即返回，无需等待 LLM）
        """
        task_id = str(uuid.uuid4())

        # 每次创建新任务时，摇销清理过期任务（防止内存泄漏）
        _cleanup_expired_tasks()

        # 立即注册任务，状态为 PROCESSING（LLM 准备中）
        _save_task(task_id, {
            'status': 'PROCESSING',
            'zimage_task_id': None,
            'prompt': None,
            'negative_prompt': '',
            'image_url': None,
            'error': None
        })

        def _run():
            # 提取 role_config 中的各项上下文
            appearance_tags = role_config.get('appearance_tags', '')
            current_clothing = role_config.get('clothing_state', '')
            default_scene = role_config.get('default_scene', '')

            try:
                # 第一步：场景分析
                print(
                    f"[Image] 场景分析输入 - 衣物: {current_clothing!r}, 场景: {default_scene!r}")
                scene_description, scene_clothing_state = ImageService.analyze_scene(
                    chat_history,
                    appearance_tags,
                    current_clothing=current_clothing,
                    default_scene=default_scene
                )

                # 第二步：自然语言视觉描述（直接作为最终 prompt 使用，跳过第三步）
                visual_description = ImageService.generate_visual_description(
                    scene_description=scene_description,
                    role_config=role_config
                )

                # 追加风格描述和基础约束（简洁版，控制长度）
                config = get_image_generation_config()
                styles = config.get('styles', {})
                style_data = styles.get(role_config.get(
                    'image_style', 'anime'), styles.get('anime', {}))
                style_desc = style_data.get('style_desc', '')

                # 构建简洁 prompt：视觉描述 + 风格 + 精简约束
                final_prompt = f"{visual_description} {style_desc}".strip()
                # 追加精简约束（避免过长）
                constraints = "no extra limbs, no deformed hands, no watermark, anatomically correct"
                if 'nude' in final_prompt.lower() or 'bare' in final_prompt.lower():
                    constraints += ", anatomically accurate nudity"
                final_prompt = f"{final_prompt}. {constraints}."
                # 截断到 1950 字符以内
                final_prompt = _truncate_prompt(final_prompt)

                negative_prompt = ""

                print("=" * 80)
                print("[Image] ====== 文生图两步流程日志 (测试模式) ======")
                print("=" * 80)
                print(f"\n[Image] 【输入】聊天记录:\n{chat_history}\n")
                print(f"[Image] [步骤1]场景分析结果:\n{scene_description}\n")
                print(
                    f"[Image] [步骤2]视觉描述直接作为Prompt ({len(final_prompt)} chars):\n{final_prompt[:500]}...\n")

                # 提交 Z-image 任务
                zimage_task_id = ImageService.generate_image_async(
                    final_prompt, negative_prompt)

                if not zimage_task_id:
                    print("[Image] 创建 Z-image 任务失败")
                    _update_task(
                        task_id, {'status': 'ERROR', 'error': '提交图像生成任务失败'})
                    return

                print(
                    f"[Image] 创建任务成功: local={task_id}, zimage={zimage_task_id}")
                _update_task(task_id, {
                    'status': 'PENDING',
                    'zimage_task_id': zimage_task_id,
                    'prompt': final_prompt,
                    'negative_prompt': negative_prompt
                })

            except Exception as e:
                print(f"[Image] 后台任务异常: {e}")
                _update_task(task_id, {'status': 'ERROR', 'error': str(e)})

        # 在后台线程执行三步 LLM 流程，不阻塞 HTTP 请求
        t = threading.Thread(target=_run, daemon=True)
        t.start()

        return task_id

    @staticmethod
    def get_task_status(task_id: str) -> Dict:
        """获取任务状态"""
        task = _get_task(task_id)
        if not task:
            print(f"[Image] 任务不存在: {task_id}")
            return {'status': 'ERROR', 'error': '任务不存在或已过期'}

        print(f"[Image] 找到任务: zimage_task_id={task.get('zimage_task_id')}")

        # 如果任务还在处理中，查询 Z-image 状态（仅 PENDING 状态才需要查）
        if task['status'] == 'PENDING' and task.get('zimage_task_id'):
            print(f"[Image] 查询 Z-image 状态: {task['zimage_task_id']}")
            zimage_status = ImageService.check_image_status(
                task['zimage_task_id'])
            print(f"[Image] Z-image 返回: {zimage_status}")

            # 更新本地状态
            if zimage_status['status'] == 'SUCCESS':
                # 下载图片到本地 cache/images/
                local_url = _download_image(zimage_status['image_url'])
                _update_task(
                    task_id, {'status': 'COMPLETED', 'image_url': local_url})
                task['status'] = 'COMPLETED'
                task['image_url'] = local_url
            elif zimage_status['status'] == 'ERROR':
                _update_task(task_id, {'status': 'ERROR',
                             'error': zimage_status['error']})
                task['status'] = 'ERROR'
                task['error'] = zimage_status['error']

        return {
            'status': task['status'],
            'image_url': task.get('image_url'),
            'error': task.get('error')
        }

    @staticmethod
    def register_zimage_task(zimage_task_id: str) -> str:
        """
        将一个已提交的 Z-image task_id 注册到 Redis，
        使 get_task_status 可以通过本地 task_id 轮询到状态。
        返回本地 task_id（供前端轮询使用）。
        """
        import uuid
        local_task_id = str(uuid.uuid4())
        _save_task(local_task_id, {
            'status': 'PENDING',
            'zimage_task_id': zimage_task_id,
            'image_url': None,
            'error': None,
        })
        print(
            f"[Image] 注册 Z-image 任务: local={local_task_id}, zimage={zimage_task_id}")
        return local_task_id

    @staticmethod
    def generate_image_async(prompt: str, negative_prompt: str = "") -> Optional[str]:
        """
        异步创建图像生成任务（调用 Z-image Turbo API）

        Returns:
            Z-image 的 task_id 或 None
        """
        api_key = settings.ZIMAGE_API_KEY
        if not api_key:
            print("[Image] ZIMAGE_API_KEY 未配置")
            return None

        try:
            # Z-image Turbo API 调用 - 创建任务，最多重试 3 次
            # 最终硬截断：确保不超过 API 2000 字符限制
            safe_prompt = _truncate_prompt(prompt)
            if len(prompt) != len(safe_prompt):
                print(
                    f"[Image] Prompt 截断: {len(prompt)} → {len(safe_prompt)} chars")
            last_error = None
            for attempt in range(3):
                try:
                    response = requests.post(
                        "https://zimageturbo.ai/api/generate",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "prompt": safe_prompt,
                            "negative_prompt": negative_prompt,
                            "aspect_ratio": "9:16"
                        },
                        timeout=60  # Z-image 提交可能较慢，给 60s
                    )
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("code") == 200:
                            return result.get("data", {}).get("task_id")
                        else:
                            print(f"[Image] API返回错误: {result}")
                            return None
                    else:
                        print(
                            f"[Image] API错误: {response.status_code} - {response.text}")
                        return None
                except requests.exceptions.Timeout as e:
                    last_error = e
                    print(f"[Image] Z-image 超时 (attempt {attempt + 1}/3): {e}")
                    if attempt < 2:
                        time.sleep(2)  # 等待2s再重试
            print(f"[Image] Z-image 超时全部失败: {last_error}")

        except Exception as e:
            print(f"[Image] 创建任务失败: {e}")

        return None

    @staticmethod
    def check_image_status(task_id: str) -> Dict:
        """
        查询 Z-image 任务状态

        Returns:
            {"status": "PENDING|SUCCESS|ERROR", "image_url": str, "error": str}
        """
        api_key = settings.ZIMAGE_API_KEY
        if not api_key:
            return {"status": "ERROR", "error": "ZIMAGE_API_KEY 未配置"}

        try:
            response = requests.get(
                f"https://zimageturbo.ai/api/status?task_id={task_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                print(f"[Image] Z-image status raw: {result}")
                if result.get("code") == 200:
                    data = result.get("data", {})
                    status = data.get("status", "ERROR")

                    if status == "SUCCESS":
                        # 获取图片URL列表 - response可能是数组或字符串
                        image_urls = data.get("response", [])
                        print(
                            f"[Image] response field: {image_urls}, type: {type(image_urls)}")

                        # 如果是字符串（JSON数组格式），解析它
                        if isinstance(image_urls, str):
                            try:
                                import json
                                image_urls = json.loads(image_urls)
                            except:
                                image_urls = [image_urls] if image_urls else []

                        if image_urls and len(image_urls) > 0:
                            image_url = image_urls[0] if isinstance(
                                image_urls, list) else image_urls
                            print(f"[Image] 提取图片URL: {image_url}")
                            return {
                                "status": "SUCCESS",
                                "image_url": image_url,
                                "error": None
                            }
                        else:
                            return {"status": "ERROR", "error": "无图片返回"}
                    elif status == "IN_PROGRESS":
                        return {"status": "PENDING", "image_url": None, "error": None}
                    else:
                        return {"status": "ERROR", "error": data.get("error_message", "未知错误")}
                else:
                    return {"status": "ERROR", "error": result.get("message", "API错误")}
            else:
                return {"status": "ERROR", "error": f"HTTP {response.status_code}"}

        except Exception as e:
            return {"status": "ERROR", "error": str(e)}
