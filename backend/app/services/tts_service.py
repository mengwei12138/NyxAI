"""
TTS 服务模块 (Fish Audio API)
文本转语音功能
"""
import requests
import os
import hashlib
from typing import List, Dict, Any, Optional
from app.config import get_settings
from app.services.oss_service import OssService

settings = get_settings()

# 音频缓存目录
CACHE_DIR = os.path.join(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'cache', 'tts')
os.makedirs(CACHE_DIR, exist_ok=True)

# 预览音频专用目录
PREVIEW_DIR = os.path.join(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'cache', 'tts_preview')
os.makedirs(PREVIEW_DIR, exist_ok=True)


def get_voice_presets(session=None) -> List[Dict[str, Any]]:
    """
    从数据库读取激活的音色预设列表，按 sort_order 排序。
    session 为 None 时自动创建一个临时 session。
    返回字典列表（兼容旧代码格式）。
    """
    try:
        from app.models.voice import VoicePreset
        from sqlmodel import select, Session
        from app.database import engine

        def _fetch(sess):
            presets = sess.exec(
                select(VoicePreset)
                .where(VoicePreset.is_active == True)
                .order_by(VoicePreset.sort_order)
            ).all()
            return [
                {
                    "id": p.preset_id,
                    "name": p.name,
                    "description": p.description or "",
                    "reference_id": p.reference_id,
                    "preview_text": p.preview_text or "",
                    "is_default": p.is_default,
                }
                for p in presets
            ]

        if session is not None:
            return _fetch(session)
        with Session(engine) as s:
            return _fetch(s)
    except Exception as e:
        print(f"[TTS] 读取音色预设失败，使用内置默认: {e}")
        # 降级到内置默认，确保服务可用
        return [
            {
                "id": "wenrou_yujie",
                "name": "温柔御姐",
                "description": "温婉柔和，知性大方",
                "reference_id": "5c09bfed66ce4a968c3022d6f85c8e07",
                "preview_text": "今天辛苦了吧，来，让我帮你放松一下。",
                "is_default": True,
            },
        ]


def get_default_voice_id(session=None) -> str:
    """
    获取全局默认音色的 Fish Audio reference_id。
    优先取数据库中 is_default=True 的记录，找不到则 fallback 到配置项。
    """
    try:
        from app.models.voice import VoicePreset
        from sqlmodel import select, Session
        from app.database import engine

        def _fetch(sess):
            preset = sess.exec(
                select(VoicePreset)
                .where(VoicePreset.is_default == True, VoicePreset.is_active == True)
            ).first()
            return preset.reference_id if preset else None

        ref_id = _fetch(session) if session is not None else None
        if ref_id is None:
            from sqlmodel import Session
            from app.database import engine
            with Session(engine) as s:
                ref_id = _fetch(s)

        return ref_id or getattr(settings, 'SYSTEM_ROLE_VOICE_ID', '5c09bfed66ce4a968c3022d6f85c8e07')
    except Exception:
        return getattr(settings, 'SYSTEM_ROLE_VOICE_ID', '5c09bfed66ce4a968c3022d6f85c8e07')


def get_cache_path(text: str, reference_id: str = None) -> str:
    """根据文本和声音模型生成缓存文件路径（同文本+同声音才命中缓存）"""
    cache_key = f"{reference_id or 'default'}:{text}"
    text_hash = hashlib.md5(cache_key.encode('utf-8')).hexdigest()
    return os.path.join(CACHE_DIR, f"{text_hash}.mp3")


def get_preview_path(voice_id: str) -> str:
    """获取音色预览文件路径"""
    return os.path.join(PREVIEW_DIR, f"preview_{voice_id}.mp3")


# 进程内已上传 OSS 的 key 集合，避免每次本地命中缓存都发 HEAD 请求
_oss_uploaded_keys: set = set()


def _upload_audio_to_oss(local_path: str, oss_prefix: str = "tts") -> None:
    """
    将音频文件上传到 OSS（仅在 OSS 已启用时执行，进程内已上传则跳过）。
    """
    if not OssService.is_enabled():
        return
    filename = os.path.basename(local_path)
    oss_key = f"{oss_prefix}/{filename}"
    if oss_key in _oss_uploaded_keys:
        return
    OssService.upload_file(local_path, oss_key)
    _oss_uploaded_keys.add(oss_key)


def _restore_from_oss(local_path: str, oss_prefix: str = "tts") -> bool:
    """
    本地文件不存在时，尝试从 OSS 流式下载恢复到本地。
    返回是否成功。
    """
    if not OssService.is_enabled():
        return False
    filename = os.path.basename(local_path)
    oss_key = f"{oss_prefix}/{filename}"
    ok = OssService.download_stream(oss_key, local_path)
    if ok:
        print(f"[TTS-OSS] 从 OSS 恢复本地缓存: {oss_key}")
        _oss_uploaded_keys.add(oss_key)  # 标记已存在
    else:
        print(f"[TTS-OSS] OSS 无缓存: {oss_key}")
    return ok


def generate_voice_preview(voice_id: str) -> str:
    """
    生成音色试听音频，返回文件路径

    Args:
        voice_id: 音色 ID（数据库 preset_id 字段）

    Returns:
        音频文件路径，失败返回 None
    """
    # 从数据库查找音色预设
    presets = get_voice_presets()
    preset = next((v for v in presets if v["id"] == voice_id), None)
    if not preset:
        print(f"[TTS Preview] 音色 {voice_id} 不存在")
        return None

    preview_path = get_preview_path(voice_id)

    # 已有缓存直接返回
    if os.path.exists(preview_path):
        print(f"[TTS Preview] 使用缓存: {preview_path}")
        return preview_path

    # 生成预览语音
    print(f"[TTS Preview] 生成 {preset['name']} 的试听音频...")
    result = generate_speech(
        text=preset["preview_text"],
        reference_id=preset["reference_id"],
        use_cache=False,
        output_path=preview_path,
    )
    return result


def generate_speech(text: str, reference_id: str = None, use_cache: bool = True, output_path: str = None) -> tuple[str, str | None]:
    """
    生成语音，返回 (本地文件路径, OSS URL or None)

    Args:
        text: 要转换的文本
        reference_id: 声音模型 ID（可选）
        use_cache: 是否使用缓存
        output_path: 指定输出路径（可选）

    Returns:
        (audio_path, oss_url)，失败返回 (None, None)
    """
    def _with_oss(local_path: str) -> tuple[str, str | None]:
        """上传并返回 (local_path, oss_url)"""
        _upload_audio_to_oss(local_path)
        filename = os.path.basename(local_path)
        oss_key = f"tts/{filename}"
        if OssService.is_enabled() and oss_key in _oss_uploaded_keys:
            return local_path, OssService.get_public_url(oss_key)
        return local_path, None
    api_key = settings.FISH_AUDIO_API_KEY if hasattr(
        settings, 'FISH_AUDIO_API_KEY') else None

    if not api_key:
        print("[TTS] 错误: FISH_AUDIO_API_KEY 未配置")
        return None, None

    if not text or not text.strip():
        print("[TTS] 错误: 文本为空")
        return None, None

    # 检查缓存（text + voice 双维度）
    cache_path = output_path or get_cache_path(text, reference_id)
    if use_cache and os.path.exists(cache_path):
        print(f"[TTS] 使用本地缓存: {cache_path}")
        return _with_oss(cache_path)

    # 本地不存在时，尝试从 OSS 恢复（避免重新调 Fish Audio API 扣费）
    if use_cache and OssService.is_enabled():
        if _restore_from_oss(cache_path):
            return _with_oss(cache_path)

    try:
        # 调用 Fish Audio API
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "text": text,
            "reference_id": reference_id or get_default_voice_id(),
            "format": "mp3",
            "model": "s1"
        }

        response = requests.post(
            "https://api.fish.audio/v1/tts",
            headers=headers,
            json=data,
            timeout=60
        )

        if response.status_code == 200:
            with open(cache_path, 'wb') as f:
                f.write(response.content)
            print(f"[TTS] 生成成功: {cache_path}")
            return _with_oss(cache_path)
        elif response.status_code == 400 and "Reference not found" in response.text:
            fallback_id = get_default_voice_id()
            print(
                f"[TTS] 声音模型 {reference_id} 无效，使用系统默认声音 {fallback_id}")
            data["reference_id"] = fallback_id
            response = requests.post(
                "https://api.fish.audio/v1/tts",
                headers=headers,
                json=data,
                timeout=60
            )
            if response.status_code == 200:
                with open(cache_path, 'wb') as f:
                    f.write(response.content)
                print(f"[TTS] 使用默认声音生成成功: {cache_path}")
                return _with_oss(cache_path)
            else:
                print(
                    f"[TTS] 默认声音也失败: {response.status_code} - {response.text}")
                return None, None
        else:
            print(f"[TTS] API错误: {response.status_code} - {response.text}")
            return None, None

    except Exception as e:
        print(f"[TTS] 异常: {e}")
        return None, None
