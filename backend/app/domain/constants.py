"""领域常量与枚举（《03-数据模型设计》）。

常量集中定义，禁止在业务代码中散落魔法字符串。
"""

# ==================== 用户状态 ====================
USER_STATUS_DISABLED = 0
USER_STATUS_ACTIVE = 1

# ==================== 登录方式（sys_login_log.login_method）====================
LOGIN_METHOD_LOCAL = "local"
LOGIN_METHOD_DINGTALK = "dingtalk"

# ==================== 外部身份 Provider（sys_user_identity.provider）====================
IDENTITY_PROVIDER_DINGTALK = "dingtalk"

# ==================== 内置角色编码 ====================
ROLE_SUPER_ADMIN = "super_admin"
ROLE_ADMIN = "admin"
ROLE_USER = "user"

# ==================== 权限点编码（模块:动作）====================
PERM_AUTH_LOGIN = "auth:login"
PERM_AUTH_ME = "auth:me"
PERM_CONFIG_DINGTALK_READ = "config:dingtalk:read"
PERM_CONFIG_DINGTALK_WRITE = "config:dingtalk:write"
PERM_CONFIG_DINGTALK_TEST = "config:dingtalk:test"
PERM_ADMIN_USER_MANAGE = "user:manage"

# ==================== 系统配置键 ====================
CONFIG_KEY_DINGTALK = "dingtalk"

# ==================== Redis 键前缀（命名规范：业务域:对象:标识）====================
REDIS_REFRESH_PREFIX = "auth:refresh:"
REDIS_BLACKLIST_PREFIX = "auth:blacklist:"
REDIS_DINGTALK_STATE_PREFIX = "oauth:dingtalk:state:"
REDIS_RATELIMIT_LOGIN_PREFIX = "ratelimit:login:"
REDIS_RATELIMIT_LOGIN_FAIL_PREFIX = "ratelimit:login_fail:"
REDIS_CONFIG_CACHE_PREFIX = "cache:config:"

# ==================== 限流参数 ====================
LOGIN_RATE_LIMIT_PER_MINUTE = 10
LOGIN_FAIL_LIMIT = 5
LOGIN_FAIL_LOCK_MINUTES = 15

# ==================== 钉钉 OAuth 参数 ====================
DINGTALK_AUTHORIZE_URL = "https://login.dingtalk.com/oauth2/auth"
# 新接口 API 网关域名：api.dingtalk.com（v1.0 新接口；存量企业内部应用凭证在此网关生效，api.dingtalk.io 会返回 invalid_client）
DINGTALK_TOKEN_URL = "https://api.dingtalk.com/v1.0/oauth2/userAccessToken"
DINGTALK_USER_INFO_URL = "https://api.dingtalk.com/v1.0/contact/users/me"
# 新版推荐：应用凭证接口（单组织/多组织统一），corpId 为应用运行企业的组织 ID
DINGTALK_APP_TOKEN_URL_TEMPLATE = "https://api.dingtalk.com/v1.0/oauth2/{corp_id}/token"
DINGTALK_APP_TOKEN_GRANT_TYPE = "client_credentials"
DINGTALK_STATE_TTL_SECONDS = 600  # 10 分钟

# 最新 OAuth 授权参数（官方《实现网页方式登录应用》）
DINGTALK_RESPONSE_TYPE = "code"
DINGTALK_SCOPE = "openid"
DINGTALK_PROMPT = "consent"