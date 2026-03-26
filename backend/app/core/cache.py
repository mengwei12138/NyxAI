"""
轻量级内存缓存模块
用于缓解 Supabase 跨洋延迟，减少高频只读接口的数据库查询
"""
import time
import asyncio
from typing import Any, Optional, Callable, TypeVar
from functools import wraps
from app.core.logger import get_logger

logger = get_logger("cache")

T = TypeVar("T")


class MemoryCache:
    """简单的内存 TTL 缓存"""

    def __init__(self):
        # key -> (value, expire_at)
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = asyncio.Lock()

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expire_at = entry
        if time.monotonic() > expire_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._store[key] = (value, time.monotonic() + ttl)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def delete_pattern(self, prefix: str) -> int:
        """删除所有以 prefix 开头的缓存，返回删除数量"""
        keys = [k for k in self._store if k.startswith(prefix)]
        for k in keys:
            self._store.pop(k, None)
        if keys:
            logger.debug(f"[Cache] 失效 {len(keys)} 条缓存（前缀: {prefix}）")
        return len(keys)

    def clear(self) -> None:
        self._store.clear()

    @property
    def size(self) -> int:
        # 顺便清理过期项
        now = time.monotonic()
        expired = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired:
            self._store.pop(k, None)
        return len(self._store)


# 全局单例缓存
cache = MemoryCache()

# ─── 缓存键前缀常量 ───
CACHE_ROLES_LIST = "roles:list:"      # roles:list:{mode}:{user_id}
CACHE_ROLE_DETAIL = "roles:detail:"   # roles:detail:{role_id}
CACHE_VOICE_PRESETS = "voice:presets"

# ─── TTL 常量（秒）───
TTL_ROLES_LIST = 60       # 角色列表 60 秒
TTL_ROLE_DETAIL = 120     # 角色详情 120 秒
TTL_VOICE_PRESETS = 600   # 音色预设 10 分钟（几乎不变）


def invalidate_role(role_id: int) -> None:
    """角色被修改/创建时，失效相关缓存"""
    cache.delete(f"{CACHE_ROLE_DETAIL}{role_id}")
    cache.delete_pattern(CACHE_ROLES_LIST)
    logger.debug(f"[Cache] 已失效角色 {role_id} 相关缓存")


def invalidate_all_roles() -> None:
    """失效所有角色列表缓存"""
    cache.delete_pattern(CACHE_ROLES_LIST)
    cache.delete_pattern(CACHE_ROLE_DETAIL)


# ─── Token 黑名单（兼容原有接口）───
_TOKEN_BL_PREFIX = "token_blacklist:"


async def add_token_to_blacklist(token: str, expire_seconds: int) -> None:
    """将 Token 加入黑名单"""
    cache.set(f"{_TOKEN_BL_PREFIX}{token}", True, expire_seconds)


async def is_token_blacklisted(token: str) -> bool:
    """检查 Token 是否在黑名单中"""
    return cache.get(f"{_TOKEN_BL_PREFIX}{token}") is not None
