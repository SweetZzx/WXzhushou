"""
微信路由模块
处理微信服务器的验证和消息接收
"""
from fastapi import APIRouter, Request, Query, Depends, Response
from fastapi.responses import PlainTextResponse
from typing import Optional
import hashlib
import logging

from config import WECHAT_TOKEN, WECHAT_MODE
from services.wechat import wechat_service, wechat_media_service
from services.core.agent import langchain_agent
from services.asr import ASRService
from database.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# 初始化服务
asr_service = ASRService()
# wechat_service 和 langchain_agent 是全局单例，无需初始化


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

        # 处理文本消息
        if msg_type == "text":
            # 调用 LangChain Agent 获取回复
            ai_response = await langchain_agent.process(content, from_user, db)
            logger.info(f"AI回复: {ai_response}")
            xml_response = wechat_service.create_response_xml(ai_response, from_user, to_user)
            return Response(content=xml_response, media_type="application/xml")

        # 处理语音消息
        elif msg_type == "voice":
            media_id = message.get("MediaId", "")
            if not media_id:
                logger.warning("语音消息缺少MediaId")
                xml_response = wechat_service.create_response_xml("无法识别语音消息", from_user, to_user)
                return Response(content=xml_response, media_type="application/xml")

            logger.info(f"收到语音消息: media_id={media_id}")

            # 下载语音文件
            audio_data = await wechat_media_service.download_media(media_id)
            if not audio_data:
                xml_response = wechat_service.create_response_xml("下载语音文件失败，请稍后重试", from_user, to_user)
                return Response(content=xml_response, media_type="application/xml")

            # 语音转文字
            transcribed_text = await asr_service.transcribe(audio_data)
            if not transcribed_text:
                xml_response = wechat_service.create_response_xml("语音识别失败，请稍后重试", from_user, to_user)
                return Response(content=xml_response, media_type="application/xml")

            logger.info(f"语音识别结果: {transcribed_text}")

            # 调用 LangChain Agent 处理识别后的文字
            ai_response = await langchain_agent.process(transcribed_text, from_user, db)
            logger.info(f"AI回复: {ai_response}")
            xml_response = wechat_service.create_response_xml(ai_response, from_user, to_user)
            return Response(content=xml_response, media_type="application/xml")

        # 其他消息类型
        else:
            logger.info(f"暂不支持的消息类型: {msg_type}")
            xml_response = wechat_service.create_response_xml("暂不支持此类型消息，请发送文字或语音", from_user, to_user)
            return Response(content=xml_response, media_type="application/xml")

    except Exception as e:
        logger.error(f"处理微信消息时出错: {e}", exc_info=True)
        # 返回错误信息给用户
        error_msg = f"系统错误: {str(e)}"
        try:
            xml_response = wechat_service.create_response_xml(error_msg, from_user, to_user)
            return Response(content=xml_response, media_type="application/xml")
        except:
            return Response(content="success", media_type="text/plain")
