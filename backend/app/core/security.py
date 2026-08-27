"""安全原语：密码哈希（argon2id）、JWT 签发/校验、Fernet 对称加密。

遵循《06-安全设计》：
- 密码使用 argon2id，绝不存明文；
- JWT access/refresh 分离，携带 jti 支持吊销；
- 业务密钥（钉钉 client_secret）用 Fernet 加密后入库。
"""
import base64
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

_password_hasher = PasswordHasher()


# ==================== 密码 ====================

def hash_password(plain: str) -> str:
    """使用 argon2id 哈希密码。"""
    return _password_hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """校验密码；哈希非法/不匹配均返回 False，不抛异常。"""
    try:
        return _password_hasher.verify(hashed, plain)
    except (VerifyMismatchError, InvalidHashError):
        return False


# ==================== JWT ====================

def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    user_id: int,
    *,
    roles: list[str],
    permissions: list[str],
) -> tuple[str, str]:
    """签发 access token，返回 (token, jti)。

    有效期由配置 ACCESS_TOKEN_EXPIRE_MINUTES 控制；jti 用于吊销。
    """
    settings = get_settings()
    jti = uuid.uuid4().hex
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "uid": user_id,
        "type": "access",
        "roles": roles,
        "permissions": permissions,
        "jti": jti,
        "iat": _now(),
        "exp": _now() + timedelta(minutes=settings.access_token_expire_minutes),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti


def create_refresh_token(user_id: int) -> tuple[str, str, int]:
    """签发 refresh token，返回 (token, jti, ttl_seconds)。

    refresh token 仅存于 httpOnly Cookie；Redis 记录 jti 用于轮换/吊销。
    """
    settings = get_settings()
    jti = uuid.uuid4().hex
    ttl = timedelta(days=settings.refresh_token_expire_days)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "uid": user_id,
        "type": "refresh",
        "jti": jti,
        "iat": _now(),
        "exp": _now() + ttl,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti, int(ttl.total_seconds())


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    """校验并解码 JWT；失败抛出 jwt.PyJWTError，由调用方转换为业务异常。"""
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("token type mismatch")
    return payload


# ==================== 对称加密（Fernet）====================

def _fernet() -> Fernet:
    """由配置主密钥派生 Fernet 密钥（SHA-256 → urlsafe base64）。"""
    settings = get_settings()
    digest = hashlib.sha256(settings.fernet_key.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_value(plain: str) -> str:
    """加密敏感值（如钉钉 client_secret），返回 urlsafe base64 密文。"""
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_value(cipher: str) -> str:
    """解密敏感值；密文非法时抛 BizException 语义由调用方处理。"""
    try:
        return _fernet().decrypt(cipher.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("invalid encrypted value") from exc