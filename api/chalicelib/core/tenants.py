from chalicelib.core import license
from chalicelib.utils import helper
from chalicelib.utils import pg_client
# 该脚本用于管理和操作租户（tenant）的信息。具体功能包括根据租户 ID 或 API 密钥获取租户信息、生成新的 API 密钥、编辑租户信息，以及检查租户是否存在。脚本的主要目标是支持租户管理系统的各项功能，通过数据库查询和更新来维护租户的状态和信息。
# 功能描述:
# 根据租户 ID 获取对应的租户信息。

# 参数:

# tenant_id: 租户的唯一标识符。
# 返回值:

# 返回一个字典格式的租户信息，包括租户 ID、名称、API 密钥、创建时间、版本号和选择退出状态。
def get_by_tenant_id(tenant_id):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(f"""SELECT tenants.tenant_id,
                                       tenants.name,
                                       tenants.api_key,
                                       tenants.created_at,
                                       '{license.EDITION}' AS edition,
                                       openreplay_version() AS version_number,
                                       tenants.opt_out
                                FROM public.tenants
                                LIMIT 1;""",
                            {"tenantId": tenant_id})
        cur.execute(query=query)
        return helper.dict_to_camel_case(cur.fetchone())

# 功能描述:
# 根据租户的 API 密钥获取租户信息。

# 参数:

# api_key: 用于识别租户的 API 密钥。
# 返回值:

# 返回一个字典格式的租户信息，包括租户 ID、名称和创建时间。
def get_by_api_key(api_key):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(f"""SELECT 1 AS tenant_id,
                                       tenants.name,
                                       tenants.created_at                       
                                FROM public.tenants
                                WHERE tenants.api_key = %(api_key)s
                                LIMIT 1;""",
                            {"api_key": api_key})
        cur.execute(query=query)
        return helper.dict_to_camel_case(cur.fetchone())

# 功能描述:
# 为指定的租户生成一个新的 API 密钥。

# 参数:

# tenant_id: 租户的唯一标识符。
# 返回值:

# 返回一个字典格式的租户信息，包括新生成的 API 密钥。
def generate_new_api_key(tenant_id):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(f"""UPDATE public.tenants
                                SET api_key=generate_api_key(20)
                                RETURNING api_key;""",
                            {"tenant_id": tenant_id})
        cur.execute(query=query)
        return helper.dict_to_camel_case(cur.fetchone())

# 功能描述:
# 编辑和更新指定租户的相关信息。

# 参数:

# tenant_id: 租户的唯一标识符。
# changes: 需要更新的字段和值的字典。
# 返回值:

# 返回更新后的租户信息，包括名称和选择退出状态。
def edit_tenant(tenant_id, changes):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(f"""UPDATE public.tenants 
                                SET {", ".join([f"{helper.key_to_snake_case(k)} = %({k})s" for k in changes.keys()])}  
                                RETURNING name, opt_out;""",
                            {"tenant_id": tenant_id, **changes})
        cur.execute(query=query)
        return helper.dict_to_camel_case(cur.fetchone())

# 功能描述:
# 同步检查租户是否存在。

# 参数:

# use_pool: 是否使用数据库连接池。
# 返回值:

# 如果存在至少一个租户，返回 True，否则返回 False。
def tenants_exists_sync(use_pool=True):
    with pg_client.PostgresClient(use_pool=use_pool) as cur:
        cur.execute("SELECT EXISTS(SELECT 1 FROM public.tenants)")
        out = cur.fetchone()["exists"]
        return out

# 功能描述:
# 异步检查租户是否存在。

# 参数:

# use_pool: 是否使用数据库连接池。
# 返回值:

# 如果存在至少一个租户，返回 True，否则返回 False。
async def tenants_exists(use_pool=True):
    from app import app
    async with app.state.postgresql.connection() as cnx:
        async with cnx.transaction() as txn:
            row = await cnx.execute("SELECT EXISTS(SELECT 1 FROM public.tenants)")
            row = await row.fetchone()
            return row["exists"]
