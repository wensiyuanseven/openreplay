# 这段代码的主要功能是处理用户对特定会话（session）的收藏操作。
# 包括添加、移除和查询收藏会话的状态，以及获取收藏会话的时间范围（开始时间和结束时间）。这些操作在应用程序中可能用于管理和显示用户收藏的会话列表。
import schemas
from chalicelib.utils import pg_client

# 功能描述：
# 将指定的会话（session）添加到用户的收藏列表中。

# 参数：
# context: schemas.CurrentContext 对象，包含当前用户的上下文信息（如 user_id）。
# project_id: 项目ID（未在函数中使用，但通常与会话相关）。
# session_id: 会话ID。
# 返回值：
# dict: 如果操作成功，返回包含 sessionId 的数据；如果操作失败，返回错误信息。
# 代码详解：
# 使用用户ID和会话ID将会话添加到 user_favorite_sessions 表中。
# 如果插入成功，返回 sessionId；否则返回错误信息。
def add_favorite_session(context: schemas.CurrentContext, project_id, session_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(f"""\
                INSERT INTO public.user_favorite_sessions(user_id, session_id) 
                VALUES (%(userId)s,%(session_id)s)
                RETURNING session_id;""",
                        {"userId": context.user_id, "session_id": session_id})
        )
        row = cur.fetchone()
    if row:
        return {"data": {"sessionId": session_id}}
    return {"errors": ["something went wrong"]}

# 函数：remove_favorite_session
# 功能描述：
# 从用户的收藏列表中移除指定的会话。

# 参数：
# context: schemas.CurrentContext 对象，包含当前用户的上下文信息。
# project_id: 项目ID（未在函数中使用）。
# session_id: 会话ID。
# 返回值：
# dict: 如果操作成功，返回包含 sessionId 的数据；如果操作失败，返回错误信息。
# 代码详解：
# 使用用户ID和会话ID从 user_favorite_sessions 表中删除相应的记录。
# 如果删除成功，返回 sessionId；否则返回错误信息。
def remove_favorite_session(context: schemas.CurrentContext, project_id, session_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(f"""\
                        DELETE FROM public.user_favorite_sessions                          
                        WHERE user_id = %(userId)s
                            AND session_id = %(session_id)s
                        RETURNING session_id;""",
                        {"userId": context.user_id, "session_id": session_id})
        )
        row = cur.fetchone()
    if row:
        return {"data": {"sessionId": session_id}}
    return {"errors": ["something went wrong"]}

# 功能描述：
# 根据当前收藏状态，切换会话的收藏状态（如果已收藏则取消收藏，反之亦然）。

# 参数：
# context: schemas.CurrentContext 对象，包含当前用户的上下文信息。
# project_id: 项目ID（未在函数中使用）。
# session_id: 会话ID。
# 返回值：
# dict: 返回添加或移除收藏操作的结果。
# 代码详解：
# 调用 favorite_session_exists 函数检查会话是否已被当前用户收藏。
# 如果已收藏，则调用 remove_favorite_session 取消收藏；否则调用 add_favorite_session 添加收藏。
def favorite_session(context: schemas.CurrentContext, project_id, session_id):
    if favorite_session_exists(user_id=context.user_id, session_id=session_id):
        return remove_favorite_session(context=context, project_id=project_id,
                                       session_id=session_id)

    return add_favorite_session(context=context, project_id=project_id, session_id=session_id)

# 功能描述：
# 检查指定的会话是否已被指定的用户收藏。

# 参数：
# session_id: 会话ID。
# user_id: 用户ID（可选）。
# 返回值：
# bool: 如果会话已被收藏，返回 True；否则返回 False。
# 代码详解：
# 查询 user_favorite_sessions 表中是否存在给定 session_id 和 user_id 的记录。
# 根据查询结果返回 True 或 False。
def favorite_session_exists(session_id, user_id=None):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""SELECT session_id                                                
                    FROM public.user_favorite_sessions 
                    WHERE
                     session_id = %(session_id)s
                     {'AND user_id = %(userId)s' if user_id else ''};""",
                {"userId": user_id, "session_id": session_id})
        )
        r = cur.fetchone()
        return r is not None

# 功能描述：
# 获取指定用户在指定项目中所有收藏会话的最早和最晚的开始时间戳。

# 参数：
# project_id: 项目ID。
# user_id: 用户ID。
# 返回值：
# tuple: 返回包含最早和最晚时间戳的元组 (min_start_ts, max_start_ts)，如果没有记录则返回 (0, 0)。
# 代码详解：
# 查询 user_favorite_sessions 和 sessions 表，获取当前用户在指定项目中所有收藏会话的最早和最晚的 start_ts。
# 如果查询结果为空，返回 (0, 0)；否则返回查询的时间戳。
def get_start_end_timestamp(project_id, user_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                """SELECT max(start_ts) AS max_start_ts, min(start_ts) AS min_start_ts                                                
                    FROM public.user_favorite_sessions INNER JOIN sessions USING(session_id)
                    WHERE
                     user_favorite_sessions.user_id = %(userId)s
                     AND project_id = %(project_id)s;""",
                {"userId": user_id, "project_id": project_id})
        )
        r = cur.fetchone()
    return (0, 0) if r is None else (r["min_start_ts"], r["max_start_ts"])
