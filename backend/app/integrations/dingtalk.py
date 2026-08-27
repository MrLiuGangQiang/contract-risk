"""钉钉开放平台客户端（《04-认证与授权设计》第 3、9 节）。

- 仅面向企业内部应用：client_id = Client ID（原 AppKey），client_secret = Client Secret（原 AppSecret）；
- 所有外部调用带超时，失败统一转换为 BizException(30020)；
- 接口保持新版 /v1.0/* 路径，网关域名使用 api.dingtalk.com（存量企业内部应用凭证在此网关生效）。
"""
import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.exceptions import BizException
from app.domain.constants import (
    DINGTALK_APP_TOKEN_GRANT_TYPE,
    DINGTALK_APP_TOKEN_URL_TEMPLATE,
    DINGTALK_AUTHORIZE_URL,
    DINGTALK_PROMPT,
    DINGTALK_RESPONSE_TYPE,
    DINGTALK_SCOPE,
    DINGTALK_TOKEN_URL,
    DINGTALK_USER_INFO_URL,
)

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=10.0)

ERROR_DINGTALK = 30020


def _safe_error_detail(status_code: int, body: Any) -> str:
    """提取钉钉错误响应中的 code/message（仅超管连通性测试展示）。

    安全约束：只返回官方错误字段，绝不返回 secret、accessToken 等敏感值。
    """
    if isinstance(body, dict):
        code = body.get("code") or body.get("subCode") or str(status_code)
        message = body.get("message") or body.get("subMessage") or "未知错误"
        return f"HTTP {status_code} [{code}] {message}"
    return f"HTTP {status_code} 未知错误"


class DingTalkClient:
    """钉钉 OAuth2 客户端封装。"""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        corp_id: str,
        redirect_uri: str,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.corp_id = corp_id
        self.redirect_uri = redirect_uri

    def build_authorize_url(self, state: str) -> str:
        """构造扫码授权 URL（response_type=code, scope=openid）。

        参考：https://open.dingtalk.com/document/orgapp/tutorial-obtaining-user-personal-information.md
        """
        params = {
            "redirect_uri": self.redirect_uri,
            "response_type": DINGTALK_RESPONSE_TYPE,
            "client_id": self.client_id,
            "scope": DINGTALK_SCOPE,
            "state": state,
            "prompt": DINGTALK_PROMPT,
        }
        return f"{DINGTALK_AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code_for_token(self, auth_code: str) -> str:
        """用授权码换取用户 access_token（Client ID/Client Secret + authCode）。

        说明：authCode 为一次性凭证，仅在服务端交换，绝不下发前端。
        参考：https://help.dingtalk.io/open/development/obtain-user-token
        """
        payload = {
            "clientId": self.client_id,
            "clientSecret": self.client_secret,
            "code": auth_code,
            "grantType": "authorization_code",
        }
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.post(DINGTALK_TOKEN_URL, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("dingtalk token exchange failed: %s", exc)
            raise BizException(ERROR_DINGTALK, "钉钉授权失败") from exc

        access_token = data.get("accessToken")
        if not access_token:
            logger.warning("dingtalk token response missing accessToken: %s", data.get("code"))
            raise BizException(ERROR_DINGTALK, "钉钉授权失败")
        return access_token

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """获取当前登录用户信息（unionId/nick/avatarUrl 等）。

        参考：https://help.dingtalk.io/open/development/dingtalk-retrieve-user-information
        权限：Contact.User.Read（用户资料）；手机号需额外申请 Contact.User.mobile。
        """
        headers = {"x-acs-dingtalk-access-token": access_token}
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.get(DINGTALK_USER_INFO_URL, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("dingtalk user info failed: %s", exc)
            raise BizException(ERROR_DINGTALK, "钉钉授权失败") from exc

        if not data.get("unionId"):
            logger.warning("dingtalk user info missing unionId: %s", data.get("code"))
            raise BizException(ERROR_DINGTALK, "钉钉授权失败")
        return data

    async def get_app_access_token(self) -> str:
        """获取应用 access_token（用于连通性测试，验证 Client ID/Client Secret/CorpId）。

        新版推荐接口：POST /v1.0/oauth2/{corpId}/token
        参考：https://help.dingtalk.io/open/development/api-gettoken
        注意：应用必须已发布版本，否则 Client ID/Client Secret 无法通过此接口校验。
        """
        if not self.corp_id:
            raise BizException(ERROR_DINGTALK, "缺少企业组织 ID（CorpId），请在配置页填写")
        url = DINGTALK_APP_TOKEN_URL_TEMPLATE.format(corp_id=self.corp_id)
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": DINGTALK_APP_TOKEN_GRANT_TYPE,
        }
        status_code = 0
        body: Any = None
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.post(url, json=payload)
                status_code = resp.status_code
                try:
                    body = resp.json()
                except ValueError:
                    body = None
                resp.raise_for_status()
                data = body if isinstance(body, dict) else {}
        except (httpx.HTTPError, ValueError) as exc:
            detail = _safe_error_detail(status_code, body)
            logger.warning("dingtalk app token failed: HTTP %s %s", status_code, detail)
            raise BizException(ERROR_DINGTALK, detail) from exc

        access_token = data.get("access_token") or data.get("accessToken")
        if not access_token:
            logger.warning("dingtalk app token response missing access_token: %s", data.get("code"))
            raise BizException(ERROR_DINGTALK, "钉钉接口未返回 access_token")
        return access_token
