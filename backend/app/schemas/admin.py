"""超管配置中心 DTO（《05-API设计规范》第 3.4~3.6 节）。"""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.auth import validate_password_strength


class DingTalkConfigIn(BaseModel):
    """保存钉钉配置请求。

    client_secret 留空表示不修改（已加密存储，读取时脱敏）。
    corp_id 用于获取应用 access_token（连通性测试），登录流程不强制。
    """

    client_id: str = Field(min_length=1, max_length=128)
    client_secret: str = Field(default="", max_length=256)
    corp_id: str = Field(default="", max_length=128)
    redirect_uri: str = Field(min_length=1, max_length=512)
    enabled: bool = False


class DingTalkConfigOut(BaseModel):
    """钉钉配置响应（client_secret 已脱敏）。"""

    client_id: str
    client_secret_masked: str
    corp_id: str
    redirect_uri: str
    enabled: bool
    updated_at: datetime | None = None


class DingTalkTestResult(BaseModel):
    """钉钉连通性测试结果。"""

    ok: bool
    detail: str

# ==================== 用户与角色管理 DTO（《05-API设计规范》 2.4 节） ====================

class RoleOut(BaseModel):
    """角色响应（分配用）。"""

    id: int
    code: str
    name: str
    description: str | None = None
    is_builtin: bool
    status: int


class AdminUserOut(BaseModel):
    """用户管理列表/详情响应（含角色）。"""

    id: int
    username: str
    display_name: str
    status: int
    is_super_admin: bool
    must_change_password: bool
    roles: list[RoleOut] = Field(default_factory=list)
    created_at: datetime | None = None
    last_login_at: datetime | None = None


class AdminUserCreate(BaseModel):
    """新建用户请求。"""

    username: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    display_name: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=10, max_length=128)
    roles: list[str] = Field(default_factory=list)

    @field_validator("password")
    @classmethod
    def _validate_password_strength(cls, value: str) -> str:
        """密码策略校验（复用）。"""
        return validate_password_strength(value)


class AdminUserUpdate(BaseModel):
    """更新用户请求。"""

    display_name: str = Field(min_length=1, max_length=128)
    status: int = Field(ge=0, le=1)
    roles: list[str] = Field(default_factory=list)


class AdminUserResetPassword(BaseModel):
    """重置密码请求。"""

    password: str = Field(min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def _validate_password_strength(cls, value: str) -> str:
        """密码策略校验（复用）。"""
        return validate_password_strength(value)


class AdminUserPageOut(BaseModel):
    """用户分页响应。"""

    items: list[AdminUserOut] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


# ==================== AI 配置 DTO（《11》第 2.2 节） ====================

class AIConfigIn(BaseModel):
    """保存 AI 配置请求（api_key 留空表示不修改，已加密存储）。"""

    enabled: bool = False
    api_base: str = Field(min_length=1, max_length=256)
    api_key: str = Field(default="", max_length=512)
    model: str = Field(min_length=1, max_length=128)
    timeout_seconds: int = Field(default=30, ge=5, le=300)
    context_chars: int = Field(default=30000, ge=1000, le=200000)
    max_findings: int = Field(default=50, ge=1, le=100)


class AIConfigOut(BaseModel):
    """AI 配置响应（api_key 已脱敏）。"""

    enabled: bool = False
    api_base: str = ""
    api_key_masked: str = "***"
    model: str = ""
    timeout_seconds: int = 30
    context_chars: int = 30000
    max_findings: int = 50
    updated_at: datetime | None = None


class AITestResult(BaseModel):
    """AI 配置连通性测试结果。"""

    ok: bool = False
    detail: str = ""
