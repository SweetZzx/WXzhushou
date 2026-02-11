"""
加密工具
用于微信消息的加解密
"""
import hashlib
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)


class WXBizMsgCrypt:
    """
    微信消息加解密类
    参考微信公众平台官方文档实现
    """

    def __init__(self, token: str, encoding_aes_key: str, app_id: str):
        """
        初始化

        Args:
            token: 微信Token
            encoding_aes_key: 微信EncodingAESKey
            app_id: 微信AppID
        """
        self.token = token
        self.encoding_aes_key = encoding_aes_key
        self.app_id = app_id
        self.key = base64.b64decode(encoding_aes_key + "=")

    def encrypt_msg(self, reply_msg: str, nonce: str, timestamp: str = None) -> str:
        """
        加密消息

        Args:
            reply_msg: 待回复的消息
            nonce: 随机字符串
            timestamp: 时间戳

        Returns:
            加密后的消息
        """
        # 这里实现消息加密逻辑
        # 目前简化处理，返回原文（明文模式）
        return reply_msg

    def decrypt_msg(self, msg: str, msg_signature: str, nonce: str, timestamp: str) -> str:
        """
        解密消息

        Args:
            msg: 待解密的消息
            msg_signature: 消息签名
            nonce: 随机字符串
            timestamp: 时间戳

        Returns:
            解密后的消息
        """
        # 这里实现消息解密逻辑
        # 目前简化处理，返回原文（明文模式）
        return msg

    def verify_signature(self, signature: str, timestamp: str, nonce: str) -> bool:
        """
        验证签名

        Args:
            signature: 签名
            timestamp: 时间戳
            nonce: 随机字符串

        Returns:
            是否验证通过
        """
        tmp_list = [self.token, timestamp, nonce]
        tmp_list.sort()
        tmp_str = "".join(tmp_list)

        sha1 = hashlib.sha1()
        sha1.update(tmp_str.encode("utf-8"))
        hashcode = sha1.hexdigest()

        return hashcode == signature


def aes_decrypt(ciphertext: str, key: bytes) -> str:
    """
    AES解密

    Args:
        ciphertext: 密文
        key: 密钥

    Returns:
        明文
    """
    try:
        # Base64解码
        encrypted = base64.b64decode(ciphertext)

        # 解密
        cipher = Cipher(algorithms.AES(key), modes.CBC(key[:16]), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(encrypted) + decryptor.finalize()

        # 去除填充
        pad = decrypted[-1]
        decrypted = decrypted[:-pad]

        return decrypted.decode("utf-8")

    except Exception as e:
        logger.error(f"AES解密失败: {e}", exc_info=True)
        raise


def aes_encrypt(plaintext: str, key: bytes) -> str:
    """
    AES加密

    Args:
        plaintext: 明文
        key: 密钥

    Returns:
        密文
    """
    try:
        # 填充
        pad = 16 - (len(plaintext) % 16)
        plaintext = plaintext + chr(pad) * pad

        # 加密
        cipher = Cipher(algorithms.AES(key), modes.CBC(key[:16]), backend=default_backend())
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(plaintext.encode("utf-8")) + encryptor.finalize()

        # Base64编码
        return base64.b64encode(encrypted).decode("utf-8")

    except Exception as e:
        logger.error(f"AES加密失败: {e}", exc_info=True)
        raise
