# 这个代码片段实现了与用户查看错误（errors）相关的功能。主要包括以下内容：
# 添加用户已查看错误的记录：记录用户查看错误的行为，将其标记为已查看。
# 检查用户是否已查看某个错误：在数据库中查询用户是否已经查看了某个错误。
# 标记错误为已查看：根据用户是否已经查看该错误，决定是否将其标记为已查看。
# 用途：
# 这个模块的主要用途是追踪用户在系统中查看错误的状态，避免重复标记已查看的错误，并确保用户的查看行为被正确记录。
# 示例场景：
# 当用户第一次查看某个错误时，该错误会被标记为已查看。
# 在用户界面上，可能会通过这种标记来显示哪些错误是用户未查看过的，从而引导用户去查看新的错误信息。

from chalicelib.utils import pg_client


# 将指定的错误标记为用户已查看。
# 参数：
# - project_id: 项目ID（未使用）。
# - user_id: 用户ID，指定操作的用户。
# - error_id: 错误ID，指定要标记为已查看的错误。
def add_viewed_error(project_id, user_id, error_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                """INSERT INTO public.user_viewed_errors(user_id, error_id) 
                            VALUES (%(userId)s,%(error_id)s);""",
                {"userId": user_id, "error_id": error_id},
            )
        )


# 检查用户是否已查看指定的错误。
# 参数：
# - user_id: 用户ID，指定操作的用户。
# - error_id: 错误ID，指定要检查的错误。
# 返回值：
# - 如果用户已查看该错误，返回True；否则返回False。
def viewed_error_exists(user_id, error_id):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            """SELECT 
                    errors.error_id AS hydrated,
                    COALESCE((SELECT TRUE
                                         FROM public.user_viewed_errors AS ve
                                         WHERE ve.error_id = %(error_id)s
                                           AND ve.user_id = %(userId)s LIMIT 1), FALSE) AS viewed                                                
                FROM public.errors
                WHERE error_id = %(error_id)s""",
            {"userId": user_id, "error_id": error_id},
        )
        cur.execute(query=query)
        r = cur.fetchone()
        if r:
            return r.get("viewed")
    return True


# 标记指定错误为已查看，如果用户尚未查看该错误。
# 参数：
# - project_id: 项目ID（未使用）。
# - user_id: 用户ID，指定操作的用户。
# - error_id: 错误ID，指定要标记为已查看的错误。
# 返回值：
# - 如果用户尚未查看该错误，则标记为已查看并返回None；如果已查看，则返回None。
def viewed_error(project_id, user_id, error_id):
    if viewed_error_exists(user_id=user_id, error_id=error_id):
        return None
    return add_viewed_error(project_id=project_id, user_id=user_id, error_id=error_id)
