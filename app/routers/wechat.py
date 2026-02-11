"""
微信路由模块
处理微信服务器的验证和消息接收
"""
from fastapi import APIRouter, Request, Query, Depends, Response
from fastapi.responses import PlainTextResponse
from typing import Optional
import hashlib
import logging

from config import WECHAT_TOKEN, WECHAT_MODE, ZHIPU_API_KEY
from services.wechat_service import WeChatService
from services.agent_service import ScheduleAgentService
from database.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# 初始化服务
wechat_service = WeChatService()
agent_service = ScheduleAgentService(zhipu_api_key=ZHIPU_API_KEY)


class XMLResponse:
    """自定义XML响应类"""

    def __init__(self, content: str, status_code: int = 200, **kwargs):
        self.content = content
        self.status_code = status_code
        self.kwargs = kwargs
        # FastAPI需要的属性
        self.headers = kwargs.get('headers', {})
        self.body = content.encode('utf-8') if isinstance(content, str) else content

    async def __call__(self, scope, receive, send):
        response = Response(
            content=self.content,
            media_type="application/xml",
            status_code=self.status_code
        )
        await response(scope, receive, send)


@router.get("", response_class=PlainTextResponse)
async def wechat_verify(
    signature: str = Query(..., description="微信加密签名"),
    timestamp: str = Query(..., description="时间戳"),
    nonce: str = Query(..., description="随机数"),
    echostr: str = Query(..., description="随机字符串")
):
    """
    微信服务器验证接口

    当配置服务器URL时，微信会发送GET请求进行验证
    需要按规则返回echostr参数
    """
    logger.info(f"收到微信验证请求: signature={signature}, timestamp={timestamp}, nonce={nonce}")

    # 拼接字符串
    tmp_list = [WECHAT_TOKEN, timestamp, nonce]
    tmp_list.sort()
    tmp_str = "".join(tmp_list)

    # SHA1加密
    sha1 = hashlib.sha1()
    sha1.update(tmp_str.encode("utf-8"))
    hashcode = sha1.hexdigest()

    # 验证签名
    if hashcode == signature:
        logger.info("微信验证成功")
        return echostr
    else:
        logger.warning(f"微信验证失败: hashcode={hashcode}, signature={signature}")
        return ""


@router.post("")
async def wechat_message(request: Request, db = Depends(get_db)):
    """
    微信消息接收接口

    处理用户发送的消息并返回AI回复
    """
    from fastapi.responses import Response

    try:
        # 获取原始请求数据
        body = await request.body()
        body_str = body.decode("utf-8")
        logger.info(f"收到微信消息: {body_str}")

        # 解析XML消息
        message = wechat_service.parse_message(body_str)

        if not message:
            logger.warning("无法解析微信消息")
            return Response(content="success", media_type="text/plain")

        # 处理不同类型的消息
        msg_type = message.get("MsgType", "")
        from_user = message.get("FromUserName", "")
        to_user = message.get("ToUserName", "")
        content = message.get("Content", "")

        logger.info(f"消息类型: {msg_type}, 发送者: {from_user}, 内容: {content}")

        # 只处理文本消息
        if msg_type != "text":
            logger.info(f"暂不支持的消息类型: {msg_type}")
            xml_response = wechat_service.create_response_xml("暂不支持此类型消息", from_user, to_user)
            return Response(content=xml_response, media_type="application/xml")

        # 调用Agent获取回复
        ai_response = await agent_service.process(content, from_user, db)

        logger.info(f"AI回复: {ai_response}")

        # 返回XML格式的响应
        xml_response = wechat_service.create_response_xml(ai_response, from_user, to_user)
        return Response(content=xml_response, media_type="application/xml")

    except Exception as e:
        logger.error(f"处理微信消息时出错: {e}", exc_info=True)
        # 返回成功响应，避免微信重试
        return Response(content="success", media_type="text/plain")
