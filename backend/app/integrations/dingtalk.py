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
    DINGTALK_MICROAPP_USER_INFO_URL,
    DINGTALK_PROMPT,
    DINGTALK_RESPONSE_TYPE,
    DINGTALK_SCOPE,
    DINGTALK_TOKEN_URL,
    DINGTALK_USER_DETAIL_URL,
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

    async def get_userid_by_auth_code(self, auth_code: str) -> dict[str, Any]:
        """用微应用免登码换取用户身份（H5 微应用免登，钉钉客户端内）。

        调用 POST /topapi/v2/user/getuserinfo（query: access_token，body: code），
        返回 result：{userid, unionid, associated_unionid, name, sys, sys_level, device_id}。
        免登码为一次性临时凭证（5 分钟有效），仅服务端使用，绝不落库/下发。
        参考：https://help.dingtalk.io/zh/open/development/obtain-the-userid-of-a-user-by-using-the-log-free
        """
        access_token = await self.get_app_access_token()
        url = f"{DINGTALK_MICROAPP_USER_INFO_URL}?access_token={access_token}"
        status_code = 0
        body: Any = None
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.post(url, json={"code": auth_code})
                status_code = resp.status_code
                try:
                    body = resp.json()
                except ValueError:
                    body = None
                resp.raise_for_status()
                data = body if isinstance(body, dict) else {}
        except (httpx.HTTPError, ValueError) as exc:
            detail = _safe_error_detail(status_code, body)
            logger.warning("dingtalk microapp userinfo failed: HTTP %s %s", status_code, detail)
            raise BizException(ERROR_DINGTALK, "钉钉免登失败") from exc

        if data.get("errcode") != 0:
            errcode = data.get("errcode")
            logger.warning("dingtalk microapp userinfo errcode=%s", errcode)
            if errcode == 40078:
                raise BizException(ERROR_DINGTALK, "钉钉免登码无效或已过期，请重试")
            raise BizException(ERROR_DINGTALK, "钉钉免登失败")
        result = data.get("result")
        if not isinstance(result, dict) or not result.get("unionid"):
            logger.warning("dingtalk microapp userinfo missing unionid")
            raise BizException(ERROR_DINGTALK, "钉钉免登失败")
        return result

    async def get_user_detail(self, user_id: str) -> dict[str, Any] | None:
        """获取钉钉用户详情（头像同步用，尽力而为）。

        免登接口不返回头像；本方法调用 topapi/v2/user/get 同步 avatar，
        需要权限 qyapi_get_member（未开通时返回 60011）。任何失败仅告警并返回 None，
        不阻断免登登录流程。
        参考：https://help.dingtalk.io/zh/open/development/query-user-details
        """
        if not user_id:
            return None
        access_token = await self.get_app_access_token()
        url = f"{DINGTALK_USER_DETAIL_URL}?access_token={access_token}"
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.post(url, json={"userid": user_id, "language": "zh_CN"})
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("dingtalk user detail failed: %s", exc)
            return None
        if data.get("errcode") != 0:
            logger.warning("dingtalk user detail errcode=%s, skip avatar", data.get("errcode"))
            return None
        result = data.get("result")
        return result if isinstance(result, dict) else None
