"""
消息数据模型
定义微信消息的数据结构
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class WeChatMessage(BaseModel):
    """微信消息模型"""

    # 基本信息
    to_user_name: str = Field(..., description="接收方账号")
    from_user_name: str = Field(..., description="发送方账号")
    create_time: int = Field(..., description="消息创建时间")
    msg_type: str = Field(..., description="消息类型")
    msg_id: Optional[str] = Field(None, description="消息ID")

    # 文本消息
    content: Optional[str] = Field(None, description="文本消息内容")

    # 图片消息
    pic_url: Optional[str] = Field(None, description="图片链接")

    # 语音消息
    media_id: Optional[str] = Field(None, description="语音媒体ID")
    format: Optional[str] = Field(None, description="语音格式")

    # 事件消息
    event: Optional[str] = Field(None, description="事件类型")
    event_key: Optional[str] = Field(None, description "事件KEY值")


class MessageRecord(BaseModel):
    """消息记录模型（用于数据库存储）"""

    id: Optional[int] = Field(None, description="记录ID")
    user_id: str = Field(..., description="用户OpenID")
    message_type: str = Field(..., description="消息类型")
    content: str = Field(..., description="消息内容")
    reply: Optional[str] = Field(None, description="AI回复内容")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

    class Config:
        from_attributes = True


class ChatHistory(BaseModel):
    """对话历史模型"""

    user_id: str = Field(..., description="用户ID")
    messages: list = Field(..., description="消息列表")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    class Config:
        from_attributes = True
