"""
用户会话管理模块
"""

import copy
from typing import Dict, Optional
from datetime import datetime, timedelta


class UserSession:
    """用户会话管理器"""

    def __init__(self, user_id: int, role_id: Optional[int] = None):
        self.user_id = user_id
        self.role_id = role_id
        self.profile = None
        self.states = None
        self.messages = []  # 对话历史
        self.last_activity = datetime.now()
        self.is_initialized = False
        self.last_message_id: Optional[int] = None  # 最近一条 AI 消息的数据库 ID

    def initialize(self, profile: dict, states: dict):
        """初始化会话"""
        self.profile = profile
        self.states = copy.deepcopy(states)
        self.messages = []
        self.is_initialized = True
        self.last_activity = datetime.now()

    def update_activity(self):
        """更新最后活动时间"""
        self.last_activity = datetime.now()

    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """检查会话是否过期"""
        return datetime.now() - self.last_activity > timedelta(minutes=timeout_minutes)


# 全局会话存储: {user_id: UserSession}
user_sessions: Dict[int, UserSession] = {}


def get_user_session(user_id: int) -> UserSession:
    """获取或创建用户会话"""
    if user_id not in user_sessions:
        user_sessions[user_id] = UserSession(user_id)
    return user_sessions[user_id]
