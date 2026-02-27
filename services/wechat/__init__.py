"""微信服务"""
from services.wechat.message import wechat_service
from services.wechat.push import wechat_push_service
from services.wechat.media import wechat_media_service

__all__ = ["wechat_service", "wechat_push_service", "wechat_media_service"]
