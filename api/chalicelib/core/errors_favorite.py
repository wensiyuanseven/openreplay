# 这个模块实现了与用户收藏的错误（errors）相关的操作功能。它允许用户将错误标记为收藏或取消收藏，并且可以检查某个错误是否已经存在以及是否已经被收藏。
from chalicelib.utils import pg_client


# 将指定的错误标记为用户的收藏。
# 参数：
# - project_id: 项目ID（未使用）
# - user_id: 用户ID，指定操作的用户。
# - error_id: 错误ID，指定要收藏的错误。
# 返回值：
# - 返回包含错误ID及其收藏状态的字典
def add_favorite_error(project_id, user_id, error_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""INSERT INTO public.user_favorite_errors(user_id, error_id) 
                            VALUES (%(userId)s,%(error_id)s);""",
                {"userId": user_id, "error_id": error_id},
            )
        )
    return {"errorId": error_id, "favorite": True}


# 取消用户对指定错误的收藏。
# 参数：
# - project_id: 项目ID（未使用）
# - user_id: 用户ID，指定操作的用户。
# - error_id: 错误ID，指定要取消收藏的错误。
# 返回值：
# - 返回包含错误ID及其取消收藏状态的字典。
def remove_favorite_error(project_id, user_id, error_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                f"""DELETE FROM public.user_favorite_errors                          
                            WHERE 
                                user_id = %(userId)s
                                AND error_id = %(error_id)s;""",
                {"userId": user_id, "error_id": error_id},
            )
        )
    return {"errorId": error_id, "favorite": False}


# 切换指定错误的收藏状态。如果错误尚未被收藏，则添加收藏；如果已被收藏，则取消收藏。
# 参数：
# - project_id: 项目ID（未使用）
# - user_id: 用户ID，指定操作的用户。
# - error_id: 错误ID，指定要操作的错误。
# 返回值：
# - 返回包含错误ID及其新收藏状态的字典。
def favorite_error(project_id, user_id, error_id):
    exists, favorite = error_exists_and_favorite(user_id=user_id, error_id=error_id)
    if not exists:
        return {"errors": ["cannot bookmark non-rehydrated errors"]}
    if favorite:
        return remove_favorite_error(project_id=project_id, user_id=user_id, error_id=error_id)
    return add_favorite_error(project_id=project_id, user_id=user_id, error_id=error_id)


# 检查指定错误是否存在，并且是否已经被当前用户收藏。
# 参数：
# - user_id: 用户ID，指定操作的用户。
# - error_id: 错误ID，指定要检查的错误。
# 返回值：
# - 返回一个元组，第一个值表示错误是否存在，第二个值表示错误是否已经被收藏。
def error_exists_and_favorite(user_id, error_id):
    with pg_client.PostgresClient() as cur:
        cur.execute(
            cur.mogrify(
                """SELECT errors.error_id AS exists, ufe.error_id AS favorite
                    FROM public.errors
                             LEFT JOIN (SELECT error_id FROM public.user_favorite_errors WHERE user_id = %(userId)s) AS ufe USING (error_id)
                    WHERE error_id = %(error_id)s;""",
                {"userId": user_id, "error_id": error_id},
            )
        )
        r = cur.fetchone()
        if r is None:
            return False, False
        return True, r.get("favorite") is not None
