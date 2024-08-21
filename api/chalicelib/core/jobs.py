# 这个文件的主要作用是管理和执行在 PostgreSQL 数据库中调度的后台任务。
# 任务通常包括删除特定用户的数据（例如删除用户的会话记录）。
# 文件中的代码提供了创建、获取、更新和取消任务的方法，以及一个执行所有已调度任务的函数。以下是文件中各个部分的详细解释：
from chalicelib.utils import pg_client, helper
from chalicelib.utils.TimeUTC import TimeUTC
from chalicelib.core import sessions_mobs, sessions_devtool


# Actions 类定义了任务的类型
class Actions:
    DELETE_USER_DATA = "delete_user_data"  # 表示删除用户数据。


# 定义了任务的不同状态
class JobStatus:
    SCHEDULED = "scheduled"  # 已调度
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


# 从数据库中获取指定的任务信息
def get(job_id, project_id):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            """SELECT *
               FROM public.jobs
               WHERE job_id = %(job_id)s
                    AND project_id= %(project_id)s;""",
            {"job_id": job_id, "project_id": project_id},
        )
        cur.execute(query=query)
        data = cur.fetchone()
        if data is None:
            return {}

        format_datetime(data)

    return helper.dict_to_camel_case(data)


# 获取指定项目的所有任务信息
def get_all(project_id):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            """SELECT *
               FROM public.jobs
               WHERE project_id = %(project_id)s;""",
            {"project_id": project_id},
        )
        cur.execute(query=query)
        data = cur.fetchall()
        for record in data:
            format_datetime(record)
    return helper.list_to_camel_case(data)


# 为指定的项目和用户创建一个新的删除用户数据的任务，并将其状态设置为 SCHEDULED。
def create(project_id, user_id):
    with pg_client.PostgresClient() as cur:
        job = {
            "status": "scheduled",
            "project_id": project_id,
            "action": Actions.DELETE_USER_DATA,
            "reference_id": user_id,
            "description": f"Delete user sessions of userId = {user_id}",
            "start_at": TimeUTC.to_human_readable(TimeUTC.midnight(1)),
        }
        # 将任务信息插入到 public.jobs 数据库表中。
        query = cur.mogrify(
            """INSERT INTO public.jobs(project_id, description, status, action,reference_id, start_at)
               VALUES (%(project_id)s, %(description)s, %(status)s, %(action)s,%(reference_id)s, %(start_at)s)
               RETURNING *;""",
            job,
        )

        cur.execute(query=query)

        r = cur.fetchone()
        format_datetime(r)
        record = helper.dict_to_camel_case(r)
    return record


# 取消任务:
def cancel_job(job_id, job):
    # 将任务状态更新为已取消
    job["status"] = JobStatus.CANCELLED
    update(job_id=job_id, job=job)


# 更新任务的状态或其他相关信息。
def update(job_id, job):
    with pg_client.PostgresClient() as cur:
        job_data = {"job_id": job_id, "errors": job.get("errors"), **job}

        query = cur.mogrify(
            """UPDATE public.jobs
               SET updated_at = timezone('utc'::text, now()),
                   status = %(status)s,
                   errors = %(errors)s
               WHERE job_id = %(job_id)s
               RETURNING *;""",
            job_data,
        )

        cur.execute(query=query)

        r = cur.fetchone()
        format_datetime(r)
        # 并将其格式化为驼峰命名的字典返回。
        record = helper.dict_to_camel_case(r)
    return record


# 将任务记录中的日期时间字段格式化为时间戳
def format_datetime(r):
    r["created_at"] = TimeUTC.datetime_to_timestamp(r["created_at"])
    r["updated_at"] = TimeUTC.datetime_to_timestamp(r["updated_at"])
    r["start_at"] = TimeUTC.datetime_to_timestamp(r["start_at"])


# 获取指定项目中指定用户的所有会话 ID。
def __get_session_ids_by_user_ids(project_id, user_ids):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            """SELECT session_id 
               FROM public.sessions
               WHERE project_id = %(project_id)s 
                    AND user_id IN %(userId)s
               LIMIT 1000;""",
            {"project_id": project_id, "userId": tuple(user_ids)},
        )
        cur.execute(query=query)
        ids = cur.fetchall()
    return [s["session_id"] for s in ids]


# 删除指定的会话记录。
def __delete_sessions_by_session_ids(session_ids):
    with pg_client.PostgresClient(unlimited_query=True) as cur:
        query = cur.mogrify(
            """DELETE FROM public.sessions
               WHERE session_id IN %(session_ids)s""",
            #    转换为元组
            {"session_ids": tuple(session_ids)},
        )
        cur.execute(query=query)


# 删除指定的会话记录相关的移动端和开发工具数据。
def __delete_session_mobs_by_session_ids(session_ids, project_id):
    sessions_mobs.delete_mobs(session_ids=session_ids, project_id=project_id)
    sessions_devtool.delete_mobs(session_ids=session_ids, project_id=project_id)


# 获取所有已调度且准备执行的任务。
def get_scheduled_jobs():
    # 从 PostgreSQL 数据库中获取已计划任务的函数
    # 当进入 with 块时，__enter__ 方法会被调用，返回一个游标 cur，用于执行数据库操作。
    # with 块结束时，__exit__ 方法会自动调用，确保数据库连接被正确关闭或释放，不管是否发生异常。
    with pg_client.PostgresClient() as cur:
        # mogrify 是 psycopg2 中游标对象的一个方法，用于将 SQL 查询字符串和参数结合，并返回一个完整的 SQL 查询字符串。
        # SQL查询是从 public.jobs 表中选择所有符合条件的记录：
        # %(status)s 是一个占位符，表示将用 {"status": JobStatus.SCHEDULED} 这个字典中的值替换。
        #
        query = cur.mogrify(
            # """...""" 是多行字符串的表示方式，允许字符串跨越多行书写。
            """SELECT *
               FROM public.jobs
               WHERE status = %(status)s 
                    AND start_at <= (now() at time zone 'utc');""",
            {"status": JobStatus.SCHEDULED},
        )
        # 这里执行了实际的 SQL 查询，query 是由 mogrify 生成的完整 SQL 语句。
        # cur.execute() 方法运行该查询并将结果存储在游标对象中。
        cur.execute(query=query)
        # fetchall() 方法用于获取所有查询结果，并将其存储在 data 变量中。
        data = cur.fetchall()
        # 这个函数将结果 data 转换为驼峰命名格式（camelCase） 用于将查询结果中的键名从下划线风格（snake_case）转换为驼峰风格
    return helper.list_to_camel_case(data)


# 执行任务
# 这个函数获取所有已调度的任务并逐个执行。对于删除用户数据的任务，它会删除与用户相关的会话记录，并更新任务的状态。
def execute_jobs():
    jobs = get_scheduled_jobs()
    for job in jobs:
        print(f"正在执行 jobId:{job['jobId']}")
        try:
            if job["action"] == Actions.DELETE_USER_DATA:
                session_ids = __get_session_ids_by_user_ids(project_id=job["projectId"], user_ids=[job["referenceId"]])
                if len(session_ids) > 0:
                    print(f"删除 {len(session_ids)} 会话")
                    __delete_sessions_by_session_ids(session_ids=session_ids)
                    __delete_session_mobs_by_session_ids(session_ids=session_ids, project_id=job["projectId"])
            else:
                raise Exception(f"这个动作 '{job['action']}' 不支持.")

            job["status"] = JobStatus.COMPLETED
            print(f"任务完成 {job['jobId']}")
        except Exception as e:
            job["status"] = JobStatus.FAILED
            job["errors"] = str(e)
            print(f"任务失败 {job['jobId']}")

        update(job["jobId"], job)
