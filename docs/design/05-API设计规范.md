# 05 API 设计规范

## 1. 通用约定

| 项 | 约定 |
| --- | --- |
| 基础路径 | `/api/v1`（版本号在 URL 中；破坏性变更升版本） |
| 资源命名 | 复数、snake_case |
| 字段命名 | 请求/响应均 snake_case |
| HTTP 动词 | GET 查询 / POST 创建与动作 / PUT 全量更新 / DELETE 删除 |
| 认证 | `Authorization: Bearer <access_token>` |
| 幂等 | 写操作如需幂等，通过请求头 `Idempotency-Key`（后续阶段启用） |

### 1.1 统一响应包裹

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "request_id": "9f8e7d6c-...",
  "timestamp": 1720000000000
}
```

- `code=0` 表示成功；失败时 `data` 为 `null`。
- `request_id` 同时返回在响应头 `X-Request-Id`，用于问题排查。

### 1.2 错误码分段

| 段 | 含义 | 示例 |
| --- | --- | --- |
| 0 | 成功 | — |
| 1xxxx | 通用业务 | 10000 通用业务错误；10001 资源不存在；10002 钉钉登录未配置或未启用；10003 请求过于频繁（限流） |
| 2xxxx | 参数校验 | 20000 参数错误；20001 参数缺失；20002 参数格式错误 |
| 3xxxx | 认证 | 30000 未认证；30001 令牌过期；30002 令牌无效；30010 账密错误；30011 账号禁用；30012 首次登录需改密；30020 钉钉授权失败；30021 state 校验失败；30013 账号已临时锁定 |
| 4xxxx | 权限 | 40000 无权限 |
| 5xxxx | 系统 | 50000 系统内部错误；50001 外部服务不可用 |

### 1.3 分页约定

请求：`page`（从 1 起）、`page_size`（默认 20，最大 100）、`sort_by`、`order`（asc/desc）。
响应 `data`：`{ "items": [], "total": 0, "page": 1, "page_size": 20 }`。

## 2. 端点清单（本阶段）

### 2.1 健康检查

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/v1/health` | 公开 | 返回服务状态、DB/Redis 连通性（部署探活用） |

### 2.2 认证（auth）

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/login` | 公开（限流） | 本地账密登录；body：`{username, password}` |
| POST | `/api/v1/auth/change-password` | 登录 | 修改密码；body：`{old_password, new_password}` |
| POST | `/api/v1/auth/logout` | 登录 | 登出并吊销令牌 |
| POST | `/api/v1/auth/refresh` | refresh cookie | 刷新令牌（轮换） |
| GET | `/api/v1/auth/dingtalk/authorize-url` | 公开 | 获取钉钉扫码授权 URL；返回 `{authorize_url, state}` |
| POST | `/api/v1/auth/dingtalk/callback` | 公开 | 钉钉授权回调；body：`{auth_code, state}` |
| GET | `/api/v1/auth/login-methods` | 公开 | 登录方式探测：返回 `{dingtalk_enabled}` |
| GET | `/api/v1/auth/me` | 登录 | 当前用户信息与权限 |

### 2.3 超管配置中心（admin）

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/v1/admin/configs/dingtalk` | `config:dingtalk:read` | 读取钉钉配置（secret 脱敏） |
| PUT | `/api/v1/admin/configs/dingtalk` | `config:dingtalk:write` | 保存钉钉配置；body：`{client_id, client_secret?, corp_id, redirect_uri, enabled}` |
| POST | `/api/v1/admin/configs/dingtalk/test` | `config:dingtalk:test` | 连通性测试（用配置调用钉钉换取 token 验证） |

> 权限说明：上述钉钉配置接口属于敏感管理接口，对非超管统一返回 404（Not Found，code=10001），与不存在路由响应一致；已认证超管无需该权限也可访问。

### 2.5 风险规则管理（admin，超管专属）

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/v1/admin/risk-rules` | `risk:rule:manage` | 规则分页列表；query：page/page_size/keyword/category/severity/enabled |
| POST | `/api/v1/admin/risk-rules` | `risk:rule:manage` | 新建规则；body：`{code,name,category,severity,keywords,description,suggestion,enabled,sort_order}` |
| PUT | `/api/v1/admin/risk-rules/{id}` | `risk:rule:manage` | 更新规则（code 不可改） |
| DELETE | `/api/v1/admin/risk-rules/{id}` | `risk:rule:manage` | 软删除规则 |
| GET | `/api/v1/admin/risk-rules/export` | `risk:rule:manage` | 导出 Markdown 附件（`text/markdown`） |
| POST | `/api/v1/admin/risk-rules/import` | `risk:rule:manage` | 导入 Markdown；body：`{content}`；返回 `{created,updated,skipped}` |

> 规则 Markdown 格式见《10-合同风险规则配置设计》；写操作写入操作审计；`risk:rule:manage` 由超管+管理员持有。

### 2.6 个人风险规则（auth，所有登录用户）

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/v1/risk-rules` | 登录 | 当前用户生效规则（全局+个人副本，个人优先） |
| PUT | `/api/v1/risk-rules/me/{code}` | 登录 | 保存个人副本 |
| DELETE | `/api/v1/risk-rules/me/{code}` | 登录 | 恢复单条默认 |
| POST | `/api/v1/risk-rules/me/restore-default` | 登录 | 一键恢复默认（前端确认） |

### 2.4 用户与角色管理（admin，超管专属）

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/v1/admin/users` | `user:manage` | 用户分页列表（含角色）；query：`page/page_size/keyword` |
| POST | `/api/v1/admin/users` | `user:manage` | 新建用户；body：`{username, display_name, password, roles[]}` |
| PUT | `/api/v1/admin/users/{user_id}` | `user:manage` | 更新用户；body：`{display_name, status, roles[]}` |
| PUT | `/api/v1/admin/users/{user_id}/password` | `user:manage` | 重置密码；body：`{password}` |
| DELETE | `/api/v1/admin/users/{user_id}` | `user:manage` | 软删除用户 |
| GET | `/api/v1/admin/roles` | `user:manage` | 角色列表（分配用） |

> 权限说明：用户与角色管理接口为敏感管理接口，对非超管统一返回 404（隐藏）；业务规则见《04-认证与授权设计》 4.4 节。

### 2.7 合同风险识别（auth，登录用户）

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | `/api/v1/contracts/upload` | 登录 | 上传合同（multipart file），同步扫描并返回结果 |
| GET | `/api/v1/contracts` | 登录 | 合同分页列表（page/page_size/keyword/severity） |
| GET | `/api/v1/contracts/{id}` | 登录 | 合同详情 + 风险列表 |
| POST | `/api/v1/contracts/{id}/rescan` | 登录 | 重新扫描 |
| DELETE | `/api/v1/contracts/{id}` | 登录 | 软删除合同 |

> 用户只能访问自己的合同；非本人返回 404 隐藏；详细设计见《11-合同风险识别核心功能设计》。

## 3. 端点详细设计

### 3.1 POST /api/v1/auth/login

请求：

```json
{ "username": "admin", "password": "******" }
```

成功响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "access_token": "eyJ...",
    "expires_in": 1800,
    "token_type": "bearer",
    "user": {
      "id": 1,
      "username": "admin",
      "display_name": "超级管理员",
      "avatar_url": null,
      "is_super_admin": true,
      "roles": ["super_admin"],
      "permissions": ["*"]
    }
  }
}
```

> refresh token 通过 `Set-Cookie`（httpOnly、Secure、SameSite=Lax）下发，不出现在响应体。

特殊错误：`30011` 账号禁用；`30012` 首次登录需改密（前端跳转改密页）。

### 3.2 GET /api/v1/auth/dingtalk/authorize-url


成功响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "authorize_url": "https://login.dingtalk.com/oauth2/auth?redirect_uri=...&response_type=code&client_id=...&scope=openid&state=...&prompt=consent",
    "state": "a1b2c3..."
  }
}
```

> 钉钉未配置或未启用时返回 `10002`（钉钉登录未配置/未启用）。

### 3.3 POST /api/v1/auth/dingtalk/callback

请求：

```json
{ "auth_code": "xxx", "state": "a1b2c3..." }
```

成功响应与 `/auth/login` 相同（返回 access_token + user）。失败返回 `30020` / `30021`。

> 钉钉授权成功回跳参数为 `authCode`、`state`，失败回跳参数为 `error`、`state`；前端回调页统一转换为 `{auth_code, state}` 后调用本接口。

### 3.4 GET /api/v1/admin/configs/dingtalk

成功响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "client_id": "dingxxxx",
    "client_secret_masked": "abc***xyz",
    "corp_id": "ding9f****41",
    "redirect_uri": "https://app.example.com/dingtalk/callback",
    "enabled": true,
    "updated_at": "2026-08-27T10:00:00+08:00"
  }
}
```

### 3.5 PUT /api/v1/admin/configs/dingtalk

请求：

```json
{
  "client_id": "dingxxxx",
  "client_secret": "new-secret-or-empty(留空表示不修改)",
  "corp_id": "ding9f****41",
  "redirect_uri": "https://app.example.com/dingtalk/callback",
  "enabled": true
}
```

成功响应：返回脱敏后的最新配置。写操作记录审计日志（`sys_operation_log`）。

### 3.6 POST /api/v1/admin/configs/dingtalk/test

成功响应：

```json
{ "code": 0, "message": "ok", "data": { "ok": true, "detail": "配置有效，已成功获取用户凭证" } }
```

失败返回 `50001` 并附失败摘要。

## 4. 错误响应示例

```json
{
  "code": 30010,
  "message": "用户名或密码错误",
  "data": null,
  "request_id": "9f8e7d6c-...",
  "timestamp": 1720000000000
}
```

## 5. 规范补充

- 所有登录类失败（本地/钉钉）返回统一文案，不暴露"用户是否存在"。
- 分页、列表类接口在 Phase 2 用户管理中统一落地。
- OpenAPI（Swagger）作为契约文档，`/docs` 在非生产环境开放。