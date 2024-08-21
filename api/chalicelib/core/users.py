# 该脚本主要用于管理租户系统中的用户信息和认证功能。通过这些功能，开发者可以实现用户的创建、更新、删除、角色管理、身份验证以及邀请成员等操作。此外，还包括对用户设置和模块状态的管理。
import json
import secrets

from decouple import config
from fastapi import BackgroundTasks

import schemas
from chalicelib.core import authorizers, metadata, projects
from chalicelib.core import tenants, assist
from chalicelib.utils import email_helper, smtp
from chalicelib.utils import helper
from chalicelib.utils import pg_client
from chalicelib.utils.TimeUTC import TimeUTC

# 功能描述:
# 生成一个用于邀请用户的安全 URL 令牌。
# 返回值:
# 返回一个长度为 64 的安全随机 URL 令牌。
def __generate_invitation_token():
    return secrets.token_urlsafe(64)

# 功能描述:
# 创建一个新的系统用户，并为其生成邀请令牌。
# 参数:
# email: 新用户的电子邮件地址。
# invitation_token: 邀请令牌，用于用户的首次登录。
# admin: 是否为管理员角色。
# name: 新用户的名字。
# owner: 是否为系统所有者角色，默认为 False。
# 返回值:
# 返回新创建用户的详细信息，包括生成的邀请令牌。
def create_new_member(email, invitation_token, admin, name, owner=False):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(f"""\
                    WITH u AS (INSERT INTO public.users (email, role, name, data)
                                VALUES (%(email)s, %(role)s, %(name)s, %(data)s)
                                RETURNING user_id,email,role,name,created_at
                            ),
                     au AS (INSERT INTO public.basic_authentication (user_id, invitation_token, invited_at)
                             VALUES ((SELECT user_id FROM u), %(invitation_token)s, timezone('utc'::text, now()))
                             RETURNING invitation_token
                            )
                    SELECT u.user_id,
                           u.email,
                           u.role,
                           u.name,
                           u.created_at,
                           (CASE WHEN u.role = 'owner' THEN TRUE ELSE FALSE END)  AS super_admin,
                           (CASE WHEN u.role = 'admin' THEN TRUE ELSE FALSE END)  AS admin,
                           (CASE WHEN u.role = 'member' THEN TRUE ELSE FALSE END) AS member,
                            au.invitation_token
                    FROM u,au;""",
                            {"email": email, "role": "owner" if owner else "admin" if admin else "member", "name": name,
                             "data": json.dumps({"lastAnnouncementView": TimeUTC.now()}),
                             "invitation_token": invitation_token})
        cur.execute(query)
        row = helper.dict_to_camel_case(cur.fetchone())
        if row:
            row["createdAt"] = TimeUTC.datetime_to_timestamp(row["createdAt"])
        return row

# 函数 restore_member
# 功能描述:
# 恢复一个已删除的用户，并为其重新生成邀请令牌。
# 参数:
# user_id: 用户的唯一标识符。
# email: 用户的电子邮件地址。
# invitation_token: 邀请令牌，用于用户的首次登录。
# admin: 是否为管理员角色。
# name: 用户的名字。
# owner: 是否为系统所有者角色，默认为 False。
# 返回值:
# 返回恢复后的用户详细信息，包括生成的邀请令牌。
def restore_member(user_id, email, invitation_token, admin, name, owner=False):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(f"""\
                    WITH ua AS (UPDATE public.basic_authentication
                                SET invitation_token = %(invitation_token)s,
                                    invited_at = timezone('utc'::text, now()),
                                    change_pwd_expire_at = NULL,
                                    change_pwd_token = NULL
                                WHERE user_id=%(user_id)s
                                RETURNING invitation_token)
                    UPDATE public.users
                    SET name= %(name)s,
                        role = %(role)s,
                        deleted_at= NULL,
                        created_at = timezone('utc'::text, now()),
                        api_key= generate_api_key(20)
                    WHERE user_id=%(user_id)s
                    RETURNING 
                           user_id,
                           email,
                           role,
                           name,
                           (CASE WHEN role = 'owner' THEN TRUE ELSE FALSE END)  AS super_admin,
                           (CASE WHEN role = 'admin' THEN TRUE ELSE FALSE END)  AS admin,
                           (CASE WHEN role = 'member' THEN TRUE ELSE FALSE END) AS member,
                           created_at,
                           (SELECT invitation_token FROM ua) AS invitation_token;""",
                            {"user_id": user_id, "email": email,
                             "role": "owner" if owner else "admin" if admin else "member",
                             "name": name, "invitation_token": invitation_token})
        cur.execute(query)
        result = cur.fetchone()
        cur.execute(query)
        result["created_at"] = TimeUTC.datetime_to_timestamp(result["created_at"])
    return helper.dict_to_camel_case(result)

# 功能描述:
# 为现有用户生成一个新的邀请令牌。
# 参数:
# user_id: 用户的唯一标识符。
# 返回值:
# 返回包含邀请令牌的邀请链接。
def generate_new_invitation(user_id):
    invitation_token = __generate_invitation_token()
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify("""\
                        UPDATE public.basic_authentication
                        SET invitation_token = %(invitation_token)s,
                            invited_at = timezone('utc'::text, now()),
                            change_pwd_expire_at = NULL,
                            change_pwd_token = NULL
                        WHERE user_id=%(user_id)s
                        RETURNING invitation_token;""",
                            {"user_id": user_id, "invitation_token": invitation_token})
        cur.execute(
            query
        )
        return __get_invitation_link(cur.fetchone().pop("invitation_token"))

# 功能描述:
# 重置用户并生成新的邀请链接。
# 参数:
# tenant_id: 租户的唯一标识符。
# editor_id: 执行重置操作的用户的唯一标识符。
# user_id_to_update: 需要重置的用户的唯一标识符。
# 返回值:
# 返回新的邀请链接。
def reset_member(tenant_id, editor_id, user_id_to_update):
    admin = get(tenant_id=tenant_id, user_id=editor_id)
    if not admin["admin"] and not admin["superAdmin"]:
        return {"errors": ["unauthorized"]}
    user = get(tenant_id=tenant_id, user_id=user_id_to_update)
    if not user:
        return {"errors": ["user not found"]}
    return {"data": {"invitationLink": generate_new_invitation(user_id_to_update)}}

# 功能描述:
# 更新用户的信息，如姓名、角色等。
# 参数:
# tenant_id: 租户的唯一标识符。
# user_id: 用户的唯一标识符。
# changes: 需要更新的字段及其新值。
# output: 是否返回更新后的用户信息，默认为 True。
# 返回值:
# 返回更新后的用户详细信息。
def update(tenant_id, user_id, changes, output=True):
    AUTH_KEYS = ["password", "invitationToken", "invitedAt", "changePwdExpireAt", "changePwdToken"]
    if len(changes.keys()) == 0:
        return None

    sub_query_users = []
    sub_query_bauth = []
    for key in changes.keys():
        if key in AUTH_KEYS:
            if key == "password":
                sub_query_bauth.append("password = crypt(%(password)s, gen_salt('bf', 12))")
                sub_query_bauth.append("changed_at = timezone('utc'::text, now())")
            else:
                sub_query_bauth.append(f"{helper.key_to_snake_case(key)} = %({key})s")
        else:
            sub_query_users.append(f"{helper.key_to_snake_case(key)} = %({key})s")

    with pg_client.PostgresClient() as cur:
        if len(sub_query_users) > 0:
            query = cur.mogrify(f"""\
                            UPDATE public.users
                            SET {" ,".join(sub_query_users)}
                            WHERE users.user_id = %(user_id)s;""",
                                {"user_id": user_id, **changes})
            cur.execute(query)
        if len(sub_query_bauth) > 0:
            query = cur.mogrify(f"""\
                            UPDATE public.basic_authentication
                            SET {" ,".join(sub_query_bauth)}
                            WHERE basic_authentication.user_id = %(user_id)s;""",
                                {"user_id": user_id, **changes})
            cur.execute(query)
    if not output:
        return None
    return get(user_id=user_id, tenant_id=tenant_id)

# 功能描述:
# 创建一个新的成员，并向其发送邀请链接。
# 参数:
# tenant_id: 租户的唯一标识符。
# user_id: 执行创建操作的用户的唯一标识符。
# data: 包含新成员详细信息的请求数据。
# background_tasks: 用于添加后台任务的对象。
# 返回值:
# 返回新创建成员的详细信息。
def create_member(tenant_id, user_id, data: schemas.CreateMemberSchema, background_tasks: BackgroundTasks):
    admin = get(tenant_id=tenant_id, user_id=user_id)
    if not admin["admin"] and not admin["superAdmin"]:
        return {"errors": ["unauthorized"]}
    if data.user_id is not None:
        return {"errors": ["please use POST/PUT /client/members/{memberId} for update"]}
    user = get_by_email_only(email=data.email)
    if user:
        return {"errors": ["user already exists"]}

    if data.name is None or len(data.name) == 0:
        data.name = data.email
    invitation_token = __generate_invitation_token()
    user = get_deleted_user_by_email(email=data.email)
    if user is not None:
        new_member = restore_member(email=data.email, invitation_token=invitation_token,
                                    admin=data.admin, name=data.name, user_id=user["userId"])
    else:
        new_member = create_new_member(email=data.email, invitation_token=invitation_token,
                                       admin=data.admin, name=data.name)
    new_member["invitationLink"] = __get_invitation_link(new_member.pop("invitationToken"))
    background_tasks.add_task(email_helper.send_team_invitation, **{
        "recipient": data.email,
        "invitation_link": new_member["invitationLink"],
        "client_id": tenants.get_by_tenant_id(tenant_id)["name"],
        "sender_name": admin["name"]
    })
    return {"data": new_member}

# 功能描述:
# 根据邀请令牌生成完整的邀请链接。
# 参数:
# invitation_token (str): 邀请令牌。
# 返回值:
# 返回完整的邀请链接。
def __get_invitation_link(invitation_token):
    return config("SITE_URL") + config("invitation_link") % invitation_token

# 功能描述:
# 允许用户更改密码，并生成一个密码修改的临时令牌。
# 参数:
# user_id: 用户的唯一标识符。
# delta_min: 密码更改链接的有效时长，默认为 10 分钟。
# 返回值:
# 返回密码修改的临时令牌。
def allow_password_change(user_id, delta_min=10):
    pass_token = secrets.token_urlsafe(8)
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(f"""UPDATE public.basic_authentication 
                                SET change_pwd_expire_at =  timezone('utc'::text, now()+INTERVAL '%(delta)s MINUTES'),
                                    change_pwd_token = %(pass_token)s
                                WHERE user_id = %(user_id)s""",
                            {"user_id": user_id, "delta": delta_min, "pass_token": pass_token})
        cur.execute(
            query
        )
    return pass_token

# 功能描述:
# 根据用户 ID 获取用户的详细信息。
# 参数:
# user_id: 用户的唯一标识符。
# tenant_id: 租户的唯一标识符。
# 返回值:
# 返回用户的详细信息。
def get(user_id, tenant_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""SELECT 
                        users.user_id,
                        email, 
                        role, 
                        name,
                        (CASE WHEN role = 'owner' THEN TRUE ELSE FALSE END)  AS super_admin,
                        (CASE WHEN role = 'admin' THEN TRUE ELSE FALSE END)  AS admin,
                        (CASE WHEN role = 'member' THEN TRUE ELSE FALSE END) AS member,
                        TRUE AS has_password,
                        settings
                    FROM public.users LEFT JOIN public.basic_authentication ON users.user_id=basic_authentication.user_id  
                    WHERE
                     users.user_id = %(userId)s
                     AND deleted_at IS NULL
                    LIMIT 1;""",
                {"userId": user_id})
        )
        r = cur.fetchone()
        return helper.dict_to_camel_case(r)

# 功能描述:
# 为指定的租户生成一个新的 API 密钥。

# 参数:

# tenant_id: 租户的唯一标识符。
# 返回值:

# 返回一个字典格式的租户信息，包括新生成的 API 密钥。
def generate_new_api_key(user_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""UPDATE public.users
                    SET api_key=generate_api_key(20)
                    WHERE users.user_id = %(userId)s
                            AND deleted_at IS NULL
                    RETURNING api_key;""",
                {"userId": user_id})
        )
        r = cur.fetchone()
    return helper.dict_to_camel_case(r)


def __get_account_info(tenant_id, user_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""SELECT users.name, 
                           tenants.name AS tenant_name, 
                           tenants.opt_out
                    FROM public.users INNER JOIN public.tenants ON(TRUE)
                    WHERE users.user_id = %(userId)s
                        AND users.deleted_at IS NULL;""",
                {"tenantId": tenant_id, "userId": user_id})
        )
        r = cur.fetchone()
    return helper.dict_to_camel_case(r)

# 功能描述:
# 更新用户账户信息，如姓名、租户名等。
# 参数:
# user_id: 用户的唯一标识符。
# tenant_id: 租户的唯一标识符。
# changes: 需要更新的字段及其新值。
# 返回值:
# 返回更新后的账户信息。
def edit_account(user_id, tenant_id, changes: schemas.EditAccountSchema):
    if changes.opt_out is not None or changes.tenantName is not None and len(changes.tenantName) > 0:
        user = get(user_id=user_id, tenant_id=tenant_id)
        if not user["superAdmin"] and not user["admin"]:
            return {"errors": ["unauthorized"]}

    if changes.name is not None and len(changes.name) > 0:
        update(tenant_id=tenant_id, user_id=user_id, changes={"name": changes.name})

    _tenant_changes = {}
    if changes.tenantName is not None and len(changes.tenantName) > 0:
        _tenant_changes["name"] = changes.tenantName

    if changes.opt_out is not None:
        _tenant_changes["opt_out"] = changes.opt_out
    if len(_tenant_changes.keys()) > 0:
        tenants.edit_tenant(tenant_id=tenant_id, changes=_tenant_changes)

    return {"data": __get_account_info(tenant_id=tenant_id, user_id=user_id)}

# 功能描述:
# 更新成员的信息，如姓名、角色等。
# 参数:
# user_id_to_update (int): 需要更新的用户的唯一标识符。
# tenant_id (int): 租户的唯一标识符。
# changes (schemas.EditMemberSchema): 需要更新的字段及其新值。
# editor_id (int): 执行更新操作的用户的唯一标识符。
# 返回值:
# 返回更新后的成员详细信息。
def edit_member(user_id_to_update, tenant_id, changes: schemas.EditMemberSchema, editor_id):
    user = get_member(user_id=user_id_to_update, tenant_id=tenant_id)
    _changes = {}
    if editor_id != user_id_to_update:
        admin = get_user_role(tenant_id=tenant_id, user_id=editor_id)
        if not admin["superAdmin"] and not admin["admin"]:
            return {"errors": ["unauthorized"]}
        if admin["admin"] and user["superAdmin"]:
            return {"errors": ["only the owner can edit his own details"]}
    else:
        if user["superAdmin"]:
            changes.admin = None
        elif changes.admin != user["admin"]:
            return {"errors": ["cannot change your own admin privileges"]}

    if changes.name and len(changes.name) > 0:
        _changes["name"] = changes.name

    if changes.admin is not None:
        _changes["role"] = "admin" if changes.admin else "member"

    if len(_changes.keys()) > 0:
        update(tenant_id=tenant_id, user_id=user_id_to_update, changes=_changes, output=False)
        return {"data": get_member(user_id=user_id_to_update, tenant_id=tenant_id)}
    return {"data": user}

# 功能描述:
# 根据电子邮件地址获取用户的详细信息。
# 参数:
# email: 用户的电子邮件地址。
# 返回值:
# 返回用户的详细信息。
def get_by_email_only(email):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""SELECT 
                        users.user_id,
                        1 AS tenant_id,
                        users.email, 
                        users.role, 
                        users.name,
                        (CASE WHEN users.role = 'owner' THEN TRUE ELSE FALSE END)  AS super_admin,
                        (CASE WHEN users.role = 'admin' THEN TRUE ELSE FALSE END)  AS admin,
                        (CASE WHEN users.role = 'member' THEN TRUE ELSE FALSE END) AS member,
                        TRUE AS has_password
                    FROM public.users LEFT JOIN public.basic_authentication ON users.user_id=basic_authentication.user_id
                    WHERE users.email = %(email)s                     
                     AND users.deleted_at IS NULL
                    LIMIT 1;""",
                {"email": email})
        )
        r = cur.fetchone()
    return helper.dict_to_camel_case(r)

# 功能描述:
# 删除特定成员。
# 参数:
# user_id (int): 当前执行删除操作的用户的唯一标识符。
# tenant_id (int): 租户的唯一标识符。
# id_to_delete (int): 需要删除的用户的唯一标识符。
# 返回值:
# 返回删除后的所有成员信息。
def get_member(tenant_id, user_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""SELECT 
                        users.user_id,
                        users.email, 
                        users.role, 
                        users.name, 
                        users.created_at,
                        (CASE WHEN users.role = 'owner' THEN TRUE ELSE FALSE END)  AS super_admin,
                        (CASE WHEN users.role = 'admin' THEN TRUE ELSE FALSE END)  AS admin,
                        (CASE WHEN users.role = 'member' THEN TRUE ELSE FALSE END) AS member,
                        DATE_PART('day',timezone('utc'::text, now()) \
                            - COALESCE(basic_authentication.invited_at,'2000-01-01'::timestamp ))>=1 AS expired_invitation,
                        basic_authentication.password IS NOT NULL AS joined,
                        invitation_token
                    FROM public.users LEFT JOIN public.basic_authentication ON users.user_id=basic_authentication.user_id 
                    WHERE users.deleted_at IS NULL AND users.user_id=%(user_id)s
                    ORDER BY name, user_id""",
                {"user_id": user_id})
        )
        u = helper.dict_to_camel_case(cur.fetchone())
        if u:
            u["createdAt"] = TimeUTC.datetime_to_timestamp(u["createdAt"])
            if u["invitationToken"]:
                u["invitationLink"] = __get_invitation_link(u.pop("invitationToken"))
            else:
                u["invitationLink"] = None

    return u

# 功能描述:
# 获取所有成员的详细信息。
# 参数:
# tenant_id (int): 租户的唯一标识符。
# 返回值:
# 返回所有成员的详细信息。
def get_members(tenant_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            f"""SELECT 
                        users.user_id,
                        users.email, 
                        users.role, 
                        users.name, 
                        users.created_at,
                        (CASE WHEN users.role = 'owner' THEN TRUE ELSE FALSE END)  AS super_admin,
                        (CASE WHEN users.role = 'admin' THEN TRUE ELSE FALSE END)  AS admin,
                        (CASE WHEN users.role = 'member' THEN TRUE ELSE FALSE END) AS member,
                        DATE_PART('day',timezone('utc'::text, now()) \
                            - COALESCE(basic_authentication.invited_at,'2000-01-01'::timestamp ))>=1 AS expired_invitation,
                        basic_authentication.password IS NOT NULL AS joined,
                        invitation_token
                    FROM public.users LEFT JOIN public.basic_authentication ON users.user_id=basic_authentication.user_id 
                    WHERE users.deleted_at IS NULL
                    ORDER BY name, user_id"""
        )
        r = cur.fetchall()
        if len(r):
            r = helper.list_to_camel_case(r)
            for u in r:
                u["createdAt"] = TimeUTC.datetime_to_timestamp(u["createdAt"])
                if u["invitationToken"]:
                    u["invitationLink"] = __get_invitation_link(u.pop("invitationToken"))
                else:
                    u["invitationLink"] = None
            return r

    return []

# 功能描述:
# 删除指定的成员用户，除非该成员是超级管理员或当前用户自己。
# 参数:
# user_id (int): 当前操作用户的唯一标识符。
# tenant_id (int): 租户的唯一标识符。
# id_to_delete (int): 需要删除的用户的唯一标识符。
# 返回值:
# 如果成功删除用户，返回删除后的所有成员列表。否则返回错误信息。
def delete_member(user_id, tenant_id, id_to_delete):
    if user_id == id_to_delete:
        return {"errors": ["unauthorized, cannot delete self"]}

    admin = get(user_id=user_id, tenant_id=tenant_id)
    if admin["member"]:
        return {"errors": ["unauthorized"]}

    to_delete = get(user_id=id_to_delete, tenant_id=tenant_id)
    if to_delete is None:
        return {"errors": ["not found"]}

    if to_delete["superAdmin"]:
        return {"errors": ["cannot delete super admin"]}

    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(f"""UPDATE public.users
                           SET deleted_at = timezone('utc'::text, now()),
                                jwt_iat= NULL, jwt_refresh_jti= NULL, 
                                jwt_refresh_iat= NULL 
                           WHERE user_id=%(user_id)s;""",
                        {"user_id": id_to_delete}))
        cur.execute(
            cur.mogrify(f"""UPDATE public.basic_authentication
                           SET password= NULL, invitation_token= NULL,
                                invited_at= NULL, changed_at= NULL,
                                change_pwd_expire_at= NULL, change_pwd_token= NULL
                           WHERE user_id=%(user_id)s;""",
                        {"user_id": id_to_delete}))
    return {"data": get_members(tenant_id=tenant_id)}

# 功能描述:
# 更改用户密码。
# 参数:
# tenant_id: 租户的唯一标识符。
# user_id: 用户的唯一标识符。
# email: 用户的电子邮件地址。
# old_password: 旧密码。
# new_password: 新密码。
# 返回值:
# 返回包含 JWT 的字典。
def change_password(tenant_id, user_id, email, old_password, new_password):
    item = get(tenant_id=tenant_id, user_id=user_id)
    if item is None:
        return {"errors": ["access denied"]}
    if old_password == new_password:
        return {"errors": ["old and new password are the same"]}
    auth = authenticate(email, old_password, for_change_password=True)
    if auth is None:
        return {"errors": ["wrong password"]}
    changes = {"password": new_password}
    user = update(tenant_id=tenant_id, user_id=user_id, changes=changes)
    r = authenticate(user['email'], new_password)

    return {
        'jwt': r.pop('jwt')
    }

# 功能描述:
# 设置用户的密码，用于接受邀请时，完成密码设置和账户激活。
# 参数:
# user_id (int): 用户的唯一标识符。
# new_password (str): 新密码。
# 返回值:
# 返回包含 JWT 令牌和用户、客户端数据的字典。
def set_password_invitation(user_id, new_password):
    changes = {"password": new_password}
    user = update(tenant_id=-1, user_id=user_id, changes=changes)
    r = authenticate(user['email'], new_password)

    tenant_id = r.pop("tenantId")
    r["limits"] = {
        "teamMember": -1,
        "projects": -1,
        "metadata": metadata.get_remaining_metadata_with_count(tenant_id)}

    c = tenants.get_by_tenant_id(tenant_id)
    c.pop("createdAt")
    c["projects"] = projects.get_projects(tenant_id=tenant_id, recorded=True)
    c["smtp"] = smtp.has_smtp()
    c["iceServers"] = assist.get_ice_servers()
    return {
        'jwt': r.pop('jwt'),
        'data': {
            "user": r,
            "client": c
        }
    }

# 功能描述:
# 检查指定电子邮件地址是否已经存在于系统中。
# 参数:
# email (str): 要检查的电子邮件地址。
# 返回值:
# 如果电子邮件存在，返回 True；否则返回 False。
def email_exists(email):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""SELECT 
                        count(user_id)                        
                    FROM public.users
                    WHERE
                     email = %(email)s
                     AND deleted_at IS NULL
                    LIMIT 1;""",
                {"email": email})
        )
        r = cur.fetchone()
    return r["count"] > 0

# 功能描述:
# 获取已删除的用户的详细信息。
# 参数:
# email (str): 用户的电子邮件地址。
# 返回值:
# 返回包含已删除用户详细信息的字典，如果没有找到，则返回 None。

def get_deleted_user_by_email(email):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""SELECT 
                        *                        
                    FROM public.users
                    WHERE
                     email = %(email)s
                     AND deleted_at NOTNULL
                    LIMIT 1;""",
                {"email": email})
        )
        r = cur.fetchone()
    return helper.dict_to_camel_case(r)

# 功能描述:
# 根据邀请令牌获取用户的详细信息。还可以根据可选的密码令牌获取信息。
# 参数:
# token (str): 邀请令牌。
# pass_token (str, optional): 用于密码更改的临时令牌。
# 返回值:
# 返回包含用户详细信息的字典。
def get_by_invitation_token(token, pass_token=None):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""SELECT 
                        *,
                        DATE_PART('day',timezone('utc'::text, now()) \
                            - COALESCE(basic_authentication.invited_at,'2000-01-01'::timestamp ))>=1 AS expired_invitation,
                        change_pwd_expire_at <= timezone('utc'::text, now()) AS expired_change,
                        (EXTRACT(EPOCH FROM current_timestamp-basic_authentication.change_pwd_expire_at))::BIGINT AS change_pwd_age
                    FROM public.users INNER JOIN public.basic_authentication USING(user_id)
                    WHERE invitation_token = %(token)s {"AND change_pwd_token = %(pass_token)s" if pass_token else ""}
                    LIMIT 1;""",
                {"token": token, "pass_token": pass_token})
        )
        r = cur.fetchone()
    return helper.dict_to_camel_case(r)

# 功能描述:
# 检查用户的身份认证信息是否存在且有效。
# 参数:
# user_id (int): 用户的唯一标识符。
# jwt_iat (int): JSON Web Token 的签发时间戳。
# 返回值:
# 如果认证信息有效，返回 True；否则返回 False。
def auth_exists(user_id, jwt_iat):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(f"""SELECT user_id, EXTRACT(epoch FROM jwt_iat)::BIGINT AS jwt_iat 
                            FROM public.users  
                            WHERE user_id = %(userId)s 
                                AND deleted_at IS NULL
                            LIMIT 1;""",
                        {"userId": user_id})
        )
        r = cur.fetchone()
    return r is not None \
        and r.get("jwt_iat") is not None \
        and abs(jwt_iat - r["jwt_iat"]) <= 1

# 功能描述:
# 检查用户的刷新令牌是否存在且有效。
# 参数:
# user_id (int): 用户的唯一标识符。
# jwt_jti (str): JSON Web Token 的唯一标识符。
# 返回值:
# 如果刷新令牌有效，返回 True；否则返回 False。
def refresh_auth_exists(user_id, jwt_jti=None):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(f"""SELECT user_id 
                            FROM public.users  
                            WHERE user_id = %(userId)s 
                                AND deleted_at IS NULL
                                AND jwt_refresh_jti = %(jwt_jti)s
                            LIMIT 1;""",
                        {"userId": user_id, "jwt_jti": jwt_jti})
        )
        r = cur.fetchone()
    return r is not None

# 功能描述:
# 更新用户的 JWT 签发时间和刷新令牌的 JTI 标识符。
# 参数:
# user_id (int): 用户的唯一标识符。
# 返回值:
# 返回新的 JWT 签发时间、刷新令牌的 JTI 标识符以及刷新令牌的签发时间。
def change_jwt_iat_jti(user_id):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(f"""UPDATE public.users
                                SET jwt_iat = timezone('utc'::text, now()-INTERVAL '10s'),
                                    jwt_refresh_jti = 0, 
                                    jwt_refresh_iat = timezone('utc'::text, now()-INTERVAL '10s') 
                                WHERE user_id = %(user_id)s 
                                RETURNING EXTRACT (epoch FROM jwt_iat)::BIGINT AS jwt_iat, 
                                          jwt_refresh_jti, 
                                          EXTRACT (epoch FROM jwt_refresh_iat)::BIGINT AS jwt_refresh_iat;""",
                            {"user_id": user_id})
        cur.execute(query)
        row = cur.fetchone()
        return row.get("jwt_iat"), row.get("jwt_refresh_jti"), row.get("jwt_refresh_iat")

# 功能描述:
# 更新用户的 JWT 签发时间，并递增刷新令牌的 JTI 标识符。
# 参数:
# user_id (int): 用户的唯一标识符。
# 返回值:
# 返回新的 JWT 签发时间、刷新令牌的 JTI 标识符以及刷新令牌的签发时间。
def refresh_jwt_iat_jti(user_id):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(f"""UPDATE public.users
                                SET jwt_iat = timezone('utc'::text, now()-INTERVAL '10s'),
                                    jwt_refresh_jti = jwt_refresh_jti + 1 
                                WHERE user_id = %(user_id)s 
                                RETURNING EXTRACT (epoch FROM jwt_iat)::BIGINT AS jwt_iat, 
                                          jwt_refresh_jti, 
                                          EXTRACT (epoch FROM jwt_refresh_iat)::BIGINT AS jwt_refresh_iat;""",
                            {"user_id": user_id})
        cur.execute(query)
        row = cur.fetchone()
        return row.get("jwt_iat"), row.get("jwt_refresh_jti"), row.get("jwt_refresh_iat")

# 功能描述:
# 验证用户的电子邮件和密码，返回用户的身份认证信息及 JWT 令牌。
# 参数:
# email (str): 用户的电子邮件地址。
# password (str): 用户的密码。
# for_change_password (bool, optional): 是否用于密码更改，默认为 False。
# 返回值:
# 如果认证成功，返回包含 JWT 令牌和用户信息的字典。如果认证失败，返回 None。
def authenticate(email, password, for_change_password=False) -> dict | bool | None:
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            f"""SELECT 
                    users.user_id,
                    1 AS tenant_id,
                    users.role,
                    users.name,
                    (CASE WHEN users.role = 'owner' THEN TRUE ELSE FALSE END)  AS super_admin,
                    (CASE WHEN users.role = 'admin' THEN TRUE ELSE FALSE END)  AS admin,
                    (CASE WHEN users.role = 'member' THEN TRUE ELSE FALSE END) AS member
                FROM public.users INNER JOIN public.basic_authentication USING(user_id)
                WHERE users.email = %(email)s 
                    AND basic_authentication.password = crypt(%(password)s, basic_authentication.password)
                    AND basic_authentication.user_id = (SELECT su.user_id FROM public.users AS su WHERE su.email=%(email)s AND su.deleted_at IS NULL LIMIT 1)
                LIMIT 1;""",
            {"email": email, "password": password})

        cur.execute(query)
        r = cur.fetchone()

    if r is not None:
        if for_change_password:
            return True
        r = helper.dict_to_camel_case(r)
        jwt_iat, jwt_r_jti, jwt_r_iat = change_jwt_iat_jti(user_id=r['userId'])
        return {
            "jwt": authorizers.generate_jwt(user_id=r['userId'], tenant_id=r['tenantId'], iat=jwt_iat,
                                            aud=f"front:{helper.get_stage_name()}"),
            "refreshToken": authorizers.generate_jwt_refresh(user_id=r['userId'], tenant_id=r['tenantId'],
                                                             iat=jwt_r_iat, aud=f"front:{helper.get_stage_name()}",
                                                             jwt_jti=jwt_r_jti),
            "refreshTokenMaxAge": config("JWT_REFRESH_EXPIRATION", cast=int),
            "email": email,
            **r
        }
    return None

# 功能描述:
# 注销用户，将用户的 JWT 信息清空。
# 参数:
# user_id (int): 用户的唯一标识符。
# 返回值:
# 无返回值。
def logout(user_id: int):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            """UPDATE public.users
               SET jwt_iat = NULL, jwt_refresh_jti = NULL, jwt_refresh_iat = NULL
               WHERE user_id = %(user_id)s;""",
            {"user_id": user_id})
        cur.execute(query)

# 功能描述:
# 刷新用户的 JWT 令牌和刷新令牌。
# 参数:
# user_id (int): 用户的唯一标识符。
# tenant_id (int, optional): 租户的唯一标识符，默认为 -1。
# 返回值:
# 返回包含新 JWT 令牌和刷新令牌的字典。
def refresh(user_id: int, tenant_id: int = -1) -> dict:
    jwt_iat, jwt_r_jti, jwt_r_iat = refresh_jwt_iat_jti(user_id=user_id)
    return {
        "jwt": authorizers.generate_jwt(user_id=user_id, tenant_id=tenant_id, iat=jwt_iat,
                                        aud=f"front:{helper.get_stage_name()}"),
        "refreshToken": authorizers.generate_jwt_refresh(user_id=user_id, tenant_id=tenant_id,
                                                         iat=jwt_r_iat, aud=f"front:{helper.get_stage_name()}",
                                                         jwt_jti=jwt_r_jti),
        "refreshTokenMaxAge": config("JWT_REFRESH_EXPIRATION", cast=int) - (jwt_iat - jwt_r_iat)
    }

# 功能描述:
# 获取用户的角色信息。
# 参数:
# tenant_id (int): 租户的唯一标识符。
# user_id (int): 用户的唯一标识符。
# 返回值:
# 返回包含用户角色信息的字典。
def get_user_role(tenant_id, user_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""SELECT 
                        users.user_id,
                        users.email, 
                        users.role, 
                        users.name, 
                        users.created_at,
                        (CASE WHEN users.role = 'owner' THEN TRUE ELSE FALSE END)  AS super_admin,
                        (CASE WHEN users.role = 'admin' THEN TRUE ELSE FALSE END)  AS admin,
                        (CASE WHEN users.role = 'member' THEN TRUE ELSE FALSE END) AS member
                    FROM public.users 
                    WHERE users.deleted_at IS NULL 
                        AND users.user_id=%(user_id)s
                    LIMIT 1""",
                {"user_id": user_id})
        )
        return helper.dict_to_camel_case(cur.fetchone())

# 功能描述:
# 获取用户的设置信息。
# 参数:
# user_id (int): 用户的唯一标识符。
# 返回值:
# 返回包含用户设置的字典。
def get_user_settings(user_id):
    #     read user settings from users.settings:jsonb column
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""SELECT 
                        settings
                    FROM public.users 
                    WHERE users.deleted_at IS NULL 
                        AND users.user_id=%(user_id)s
                    LIMIT 1""",
                {"user_id": user_id})
        )
        return helper.dict_to_camel_case(cur.fetchone())

# 功能描述:
# 更新用户的模块设置，如激活或停用某些模块。
# 参数:
# user_id (int): 用户的唯一标识符。
# data (schemas.ModuleStatus): 包含模块状态信息的数据结构。
# 返回值:
# 返回更新后的用户设置。
def update_user_module(user_id, data: schemas.ModuleStatus):
    # example data = {"settings": {"modules": ['ASSIST', 'METADATA']}
    #     update user settings from users.settings:jsonb column only update settings.modules
    #   if module property is not exists, it will be created
    #  if module property exists, it will be updated, modify here and call update_user_settings
    # module is a single element to be added or removed
    settings = get_user_settings(user_id)["settings"]
    if settings is None:
        settings = {}

    if settings.get("modules") is None:
        settings["modules"] = []

    if data.status and data.module not in settings["modules"]:
        settings["modules"].append(data.module)

    elif not data.status and data.module in settings["modules"]:
        settings["modules"].remove(data.module)

    return update_user_settings(user_id, settings)

# 功能描述:
# 更新用户的设置信息。
# 参数:
# user_id (int): 用户的唯一标识符。
# settings (dict): 要更新的设置信息。
# 返回值:
# 返回更新后的设置信息。
def update_user_settings(user_id, settings):
    #     update user settings from users.settings:jsonb column
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""UPDATE public.users
                    SET settings = %(settings)s
                    WHERE users.user_id = %(user_id)s
                            AND deleted_at IS NULL
                    RETURNING settings;""",
                {"user_id": user_id, "settings": json.dumps(settings)})
        )
        return helper.dict_to_camel_case(cur.fetchone())
