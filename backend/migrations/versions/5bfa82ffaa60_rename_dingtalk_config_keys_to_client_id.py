"""rename dingtalk config keys to client id

数据迁移（《04-认证与授权设计》第 3.4 节）：
- 将 sys_config(config_key='dingtalk') 的旧 JSON 键 app_key / app_secret_enc
  转换为 client_id / client_secret_enc；
- 幂等：仅当旧键存在时转换；可回滚（downgrade 反向转换）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5bfa82ffaa60'
down_revision: Union[str, Sequence[str], None] = 'd3ac8fc257a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONFIG_KEY = "dingtalk"

_UPDATE_SQL = sa.text(
    "UPDATE sys_config SET config_value = :value WHERE id = :id"
).bindparams(
    sa.bindparam("value", type_=postgresql.JSONB()),
    sa.bindparam("id", type_=sa.BigInteger()),
)


def _transform(value: dict, forward: bool) -> dict:
    """转换钉钉配置 JSON 键（forward=True 旧→新，False 新→旧）。"""
    out = dict(value)
    if forward:
        if "app_key" in out and "client_id" not in out:
            out["client_id"] = out.pop("app_key")
        if "app_secret_enc" in out and "client_secret_enc" not in out:
            out["client_secret_enc"] = out.pop("app_secret_enc")
    else:
        if "client_id" in out and "app_key" not in out:
            out["app_key"] = out.pop("client_id")
        if "client_secret_enc" in out and "app_secret_enc" not in out:
            out["app_secret_enc"] = out.pop("client_secret_enc")
    return out


def _migrate(forward: bool) -> None:
    """读取并转换 sys_config(config_key='dingtalk') 的配置 JSON。"""
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, config_value FROM sys_config WHERE config_key = :key"),
        {"key": CONFIG_KEY},
    ).fetchall()
    for row_id, value in rows:
        if not isinstance(value, dict):
            continue
        new_value = _transform(value, forward)
        if new_value != value:
            conn.execute(_UPDATE_SQL, {"value": new_value, "id": row_id})


def upgrade() -> None:
    """旧键 app_key/app_secret_enc → 新键 client_id/client_secret_enc。"""
    _migrate(forward=True)


def downgrade() -> None:
    """新键 client_id/client_secret_enc → 旧键 app_key/app_secret_enc。"""
    _migrate(forward=False)
