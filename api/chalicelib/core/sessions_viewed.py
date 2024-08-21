# 这段代码定义了一个名为 view_session 的函数，用于记录用户查看特定会话的操作。如果用户已经查看过该会话（即 user_viewed_sessions 表中已经存在该记录），则不会重复插入记录。
# 此功能通常用于跟踪用户与会话的交互，以便在系统中进行进一步的分析或统计。

from chalicelib.utils import pg_client


# 记录用户查看特定会话的操作。
# 参数：
# - project_id: 项目ID，用于标识数据所属的项目。
# - user_id: 用户ID，用于标识查看会话的用户。
# - session_id: 会话ID，用于标识被查看的会话。
# 返回值：
# - None: 该函数没有返回值。
def view_session(project_id, user_id, session_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                """INSERT INTO public.user_viewed_sessions(user_id, session_id) 
                            VALUES (%(userId)s,%(session_id)s)
                            ON CONFLICT DO NOTHING;""",
                {"userId": user_id, "session_id": session_id},
            )
        )
