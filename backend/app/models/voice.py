"""
音色预设模型
"""
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class VoicePreset(SQLModel, table=True):
    """音色预设表，存储 Fish Audio 声音模型配置"""
    __tablename__ = "voice_presets"

    id: Optional[int] = Field(default=None, primary_key=True)
    preset_id: str = Field(unique=True, max_length=64,
                           description="预设唯一标识，如 wenrou_yujie")
    name: str = Field(max_length=64, description="音色名称")
    description: Optional[str] = Field(
        default=None, max_length=255, description="音色描述")
    reference_id: str = Field(max_length=100, description="Fish Audio 声音模型 ID")
    preview_text: Optional[str] = Field(
        default=None, max_length=200, description="试听示例文本")
    is_default: bool = Field(default=False, description="是否为全局默认音色")
    sort_order: int = Field(default=0, description="排序权重，越小越靠前")
    is_active: bool = Field(default=True, description="是否启用")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class VoicePresetResponse(SQLModel):
    """音色预设响应模型（对外 API 使用）"""
    id: int
    preset_id: str
    name: str
    description: Optional[str]
    reference_id: str
    preview_text: Optional[str]
    is_default: bool
    sort_order: int
