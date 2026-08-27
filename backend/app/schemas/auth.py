"""认证相关 DTO（《05-API设计规范》第 3 节）。"""
import re

from pydantic import BaseModel, Field, field_validator

from app.core.exceptions import BizException


class LoginRequest(BaseModel):
    """本地账密登录请求。"""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


def validate_password_strength(value: str) -> str:
    """密码策略（《04-认证与授权设计》第 8 节）：长度 >= 10，至少三类字符。"""
    classes = 0
    if re.search(r"[a-z]", value):
        classes += 1
    if re.search(r"[A-Z]", value):
        classes += 1
    if re.search(r"\d", value):
        classes += 1
    if re.search(r"[^a-zA-Z0-9]", value):
        classes += 1
    if classes < 3:
        raise BizException(20000, "密码必须包含小写字母、大写字母、数字、特殊字符中的至少三类")
    return value


class ChangePasswordRequest(BaseModel):
    """修改密码请求。"""

    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _validate_password_strength(cls, value: str) -> str:
        """密码策略校验（复用全局函数）。"""
        return validate_password_strength(value)


class DingtalkAuthorizeResponse(BaseModel):
    """钉钉扫码授权引导信息（授权 URL + state + corp_id）。

    corp_id 供钉钉客户端内 H5 微应用免登的 requestAuthCode JSAPI 使用（非敏感）。
    """

    authorize_url: str
    state: str
    corp_id: str


class DingtalkCallbackRequest(BaseModel):
    """钉钉授权回调请求（前端携带 authCode + state）。"""

    auth_code: str = Field(min_length=1, max_length=128)
    state: str = Field(min_length=1, max_length=128)


class DingtalkMicroappLoginRequest(BaseModel):
    """钉钉 H5 微应用免登请求（前端携带 JSAPI requestAuthCode 免登码）。

    免登码 5 分钟有效、一次性，服务端不落库。
    """

    auth_code: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    """当前用户信息。"""

    id: int
    username: str
    display_name: str
    avatar_url: str | None = None
    is_super_admin: bool
    must_change_password: bool
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)

class LoginMethodsResponse(BaseModel):
    """登录方式探测响应（公开，用于前端默认展示钉钉登录）。"""

    dingtalk_enabled: bool = False


class TokenResponse(BaseModel):
    """登录/刷新成功响应（refresh token 走 httpOnly Cookie）。"""

    access_token: str
    expires_in: int
    token_type: str = "bearer"
    user: UserOut