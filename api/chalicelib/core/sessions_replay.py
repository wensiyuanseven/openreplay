# 该代码片段主要用于从数据库中获取会话相关的数据，并提供了多个函数来处理不同的数据获取需求。这些函数根据指定的项目ID和会话ID，从数据库中提取相关的事件、元数据、资源和问题信息。此外，代码还包括了处理移动会话和Web会话的特定逻辑，并提供了一些实用工具函数来辅助这些操作。最后，还有一个函数用于减少重放时显示的重复问题，以优化用户体验。
import schemas
from chalicelib.core import events, metadata, events_mobile, sessions_mobs, issues, resources, assist, sessions_devtool, sessions_notes, canvas, user_testing
from chalicelib.utils import errors_helper
from chalicelib.utils import pg_client, helper

# 检查给定的平台是否为移动平台（iOS或Android）。
# 参数：
# - platform: 平台类型的字符串，例如 'ios' 或 'android'。
# 返回值：
# - bool: 如果平台是移动平台，返回True，否则返回False。


def __is_mobile_session(platform):
    return platform in ("ios", "android")


# 组合会话和项目的元数据，将项目的元数据映射到会话数据中。
# 参数：
# - session: 字典对象，包含会话的详细信息。
# - project_metadata: 字典对象，包含项目的元数据信息。
# 返回值：
# - meta: 组合后的元数据字典。
def __group_metadata(session, project_metadata):
    meta = {}
    for m in project_metadata.keys():
        if project_metadata[m] is not None and session.get(m) is not None:
            meta[project_metadata[m]] = session[m]
        session.pop(m)
    return meta


# 根据会话ID获取会话的详细信息，包含可选的完整数据和元数据。
# 参数：
# - project_id: 项目ID，用于标识数据所属的项目。
# - session_id: 会话ID，用于标识会话。
# - context: schemas.CurrentContext类型，包含当前用户和租户的上下文信息。
# - full_data: bool类型，是否获取完整的会话数据。
# - include_fav_viewed: bool类型，是否包含用户的收藏和查看状态。
# - group_metadata: bool类型，是否组合元数据。
# - live: bool类型，是否获取实时会话信息。
# 返回值：
# - data: 包含会话详细信息的字典对象，或None如果会话未找到。
# for backward compatibility
def get_by_id2_pg(project_id, session_id, context: schemas.CurrentContext, full_data=False, include_fav_viewed=False, group_metadata=False, live=True):
    with pg_client.PostgresClient() as cur:
        extra_query = []
        if include_fav_viewed:
            extra_query.append(
                """COALESCE((SELECT TRUE
                                 FROM public.user_favorite_sessions AS fs
                                 WHERE s.session_id = fs.session_id
                                   AND fs.user_id = %(userId)s), FALSE) AS favorite"""
            )
            extra_query.append(
                """COALESCE((SELECT TRUE
                                 FROM public.user_viewed_sessions AS fs
                                 WHERE s.session_id = fs.session_id
                                   AND fs.user_id = %(userId)s), FALSE) AS viewed"""
            )
        query = cur.mogrify(
            f"""\
            SELECT
                s.*,
                s.session_id::text AS session_id,
                (SELECT project_key FROM public.projects WHERE project_id = %(project_id)s LIMIT 1) AS project_key
                {"," if len(extra_query) > 0 else ""}{",".join(extra_query)}
                {(",json_build_object(" + ",".join([f"'{m}',p.{m}" for m in metadata.column_names()]) + ") AS project_metadata") if group_metadata else ''}
            FROM public.sessions AS s {"INNER JOIN public.projects AS p USING (project_id)" if group_metadata else ""}
            WHERE s.project_id = %(project_id)s
                AND s.session_id = %(session_id)s;""",
            {"project_id": project_id, "session_id": session_id, "userId": context.user_id},
        )
        cur.execute(query=query)

        data = cur.fetchone()
        if data is not None:
            data = helper.dict_to_camel_case(data)
            if full_data:
                if __is_mobile_session(data["platform"]):
                    data["events"] = events_mobile.get_by_sessionId(project_id=project_id, session_id=session_id)
                    for e in data["events"]:
                        if e["type"].endswith("_IOS"):
                            e["type"] = e["type"][: -len("_IOS")]
                        elif e["type"].endswith("_MOBILE"):
                            e["type"] = e["type"][: -len("_MOBILE")]
                    data["crashes"] = events_mobile.get_crashes_by_session_id(session_id=session_id)
                    data["userEvents"] = events_mobile.get_customs_by_session_id(project_id=project_id, session_id=session_id)
                    data["mobsUrl"] = []
                else:
                    data["events"] = events.get_by_session_id(project_id=project_id, session_id=session_id, group_clickrage=True)
                    all_errors = events.get_errors_by_session_id(session_id=session_id, project_id=project_id)
                    data["stackEvents"] = [e for e in all_errors if e["source"] != "js_exception"]
                    # to keep only the first stack
                    # limit the number of errors to reduce the response-body size
                    data["errors"] = [errors_helper.format_first_stack_frame(e) for e in all_errors if e["source"] == "js_exception"][:500]
                    data["userEvents"] = events.get_customs_by_session_id(project_id=project_id, session_id=session_id)
                    data["domURL"] = sessions_mobs.get_urls(session_id=session_id, project_id=project_id, check_existence=False)
                    data["mobsUrl"] = sessions_mobs.get_urls_depercated(session_id=session_id, check_existence=False)
                    data["devtoolsURL"] = sessions_devtool.get_urls(session_id=session_id, project_id=project_id, check_existence=False)
                    data["resources"] = resources.get_by_session_id(session_id=session_id, project_id=project_id, start_ts=data["startTs"], duration=data["duration"])

                data["notes"] = sessions_notes.get_session_notes(tenant_id=context.tenant_id, project_id=project_id, session_id=session_id, user_id=context.user_id)
                data["metadata"] = __group_metadata(project_metadata=data.pop("projectMetadata"), session=data)
                data["issues"] = issues.get_by_session_id(session_id=session_id, project_id=project_id)
                data["live"] = live and assist.is_live(project_id=project_id, session_id=session_id, project_key=data["projectKey"])
            data["inDB"] = True
            return data
        elif live:
            return assist.get_live_session_by_id(project_id=project_id, session_id=session_id)
        else:
            return None


# 获取会话的预重放数据，主要是DOM的第一个URL。
# 参数：
# - project_id: 项目ID，用于标识数据所属的项目。
# - session_id: 会话ID，用于标识会话。
# - context: schemas.CurrentContext类型，包含当前用户和租户的上下文信息。
# 返回值：
# - dict: 包含DOM URL的字典对象。
def get_pre_replay(project_id, session_id, context: schemas.CurrentContext):
    return {"domURL": [sessions_mobs.get_first_url(project_id=project_id, session_id=session_id, check_existence=False)]}


# 获取会话的重放数据，包含完整的事件、元数据、资源和其他相关信息。
# 参数：
# - project_id: 项目ID，用于标识数据所属的项目。
# - session_id: 会话ID，用于标识会话。
# - context: schemas.CurrentContext类型，包含当前用户和租户的上下文信息。
# - full_data: bool类型，是否获取完整的会话数据。
# - include_fav_viewed: bool类型，是否包含用户的收藏和查看状态。
# - group_metadata: bool类型，是否组合元数据。
# - live: bool类型，是否获取实时会话信息。
# 返回值：
# - data: 包含会话重放数据的字典对象，或None如果会话未找到。
def get_replay(project_id, session_id, context: schemas.CurrentContext, full_data=False, include_fav_viewed=False, group_metadata=False, live=True):
    with pg_client.PostgresClient() as cur:
        extra_query = []
        if include_fav_viewed:
            extra_query.append(
                """COALESCE((SELECT TRUE
                                 FROM public.user_favorite_sessions AS fs
                                 WHERE s.session_id = fs.session_id
                                   AND fs.user_id = %(userId)s), FALSE) AS favorite"""
            )
            extra_query.append(
                """COALESCE((SELECT TRUE
                                 FROM public.user_viewed_sessions AS fs
                                 WHERE s.session_id = fs.session_id
                                   AND fs.user_id = %(userId)s), FALSE) AS viewed"""
            )
        query = cur.mogrify(
            f"""\
            SELECT
                s.*,
                s.session_id::text AS session_id,
                (SELECT project_key FROM public.projects WHERE project_id = %(project_id)s LIMIT 1) AS project_key
                {"," if len(extra_query) > 0 else ""}{",".join(extra_query)}
                {(",json_build_object(" + ",".join([f"'{m}',p.{m}" for m in metadata.column_names()]) + ") AS project_metadata") if group_metadata else ''}
            FROM public.sessions AS s {"INNER JOIN public.projects AS p USING (project_id)" if group_metadata else ""}
            WHERE s.project_id = %(project_id)s
                AND s.session_id = %(session_id)s;""",
            {"project_id": project_id, "session_id": session_id, "userId": context.user_id},
        )
        cur.execute(query=query)

        data = cur.fetchone()
        if data is not None:
            data = helper.dict_to_camel_case(data)
            if full_data:
                if __is_mobile_session(data["platform"]):
                    data["mobsUrl"] = []
                    data["videoURL"] = sessions_mobs.get_mobile_videos(session_id=session_id, project_id=project_id, check_existence=False)
                else:
                    data["mobsUrl"] = sessions_mobs.get_urls_depercated(session_id=session_id, check_existence=False)
                    data["devtoolsURL"] = sessions_devtool.get_urls(session_id=session_id, project_id=project_id, check_existence=False)
                    data["canvasURL"] = canvas.get_canvas_presigned_urls(session_id=session_id, project_id=project_id)
                    if user_testing.has_test_signals(session_id=session_id, project_id=project_id):
                        data["utxVideo"] = user_testing.get_ux_webcam_signed_url(session_id=session_id, project_id=project_id, check_existence=False)
                    else:
                        data["utxVideo"] = []

                data["domURL"] = sessions_mobs.get_urls(session_id=session_id, project_id=project_id, check_existence=False)
                data["metadata"] = __group_metadata(project_metadata=data.pop("projectMetadata"), session=data)
                data["live"] = live and assist.is_live(project_id=project_id, session_id=session_id, project_key=data["projectKey"])
            data["inDB"] = True
            return data
        elif live:
            return assist.get_live_session_by_id(project_id=project_id, session_id=session_id)
        else:
            return None


# 获取会话的事件信息，包含会话的基础数据和事件数据。
# 参数：
# - project_id: 项目ID，用于标识数据所属的项目。
# - session_id: 会话ID，用于标识会话。
# 返回值：
# - data: 包含会话事件的字典对象，或None如果会话未找到。
def get_events(project_id, session_id):
    with pg_client.PostgresClient() as cur:
        query = cur.mogrify(
            f"""SELECT session_id, platform, start_ts, duration
                FROM public.sessions AS s
                WHERE s.project_id = %(project_id)s
                    AND s.session_id = %(session_id)s;""",
            {"project_id": project_id, "session_id": session_id},
        )
        cur.execute(query=query)

        s_data = cur.fetchone()
        if s_data is not None:
            s_data = helper.dict_to_camel_case(s_data)
            data = {}
            if __is_mobile_session(s_data["platform"]):
                data["events"] = events_mobile.get_by_sessionId(project_id=project_id, session_id=session_id)
                for e in data["events"]:
                    if e["type"].endswith("_IOS"):
                        e["type"] = e["type"][: -len("_IOS")]
                    elif e["type"].endswith("_MOBILE"):
                        e["type"] = e["type"][: -len("_MOBILE")]
                data["crashes"] = events_mobile.get_crashes_by_session_id(session_id=session_id)
                data["userEvents"] = events_mobile.get_customs_by_session_id(project_id=project_id, session_id=session_id)
                data["userTesting"] = []
            else:
                data["events"] = events.get_by_session_id(project_id=project_id, session_id=session_id, group_clickrage=True)
                all_errors = events.get_errors_by_session_id(session_id=session_id, project_id=project_id)
                data["stackEvents"] = [e for e in all_errors if e["source"] != "js_exception"]
                # to keep only the first stack
                # limit the number of errors to reduce the response-body size
                data["errors"] = [errors_helper.format_first_stack_frame(e) for e in all_errors if e["source"] == "js_exception"][:500]
                data["userEvents"] = events.get_customs_by_session_id(project_id=project_id, session_id=session_id)
                data["resources"] = resources.get_by_session_id(session_id=session_id, project_id=project_id, start_ts=s_data["startTs"], duration=s_data["duration"])
                data["userTesting"] = user_testing.get_test_signals(session_id=session_id, project_id=project_id)

            data["issues"] = issues.get_by_session_id(session_id=session_id, project_id=project_id)
            data["issues"] = reduce_issues(data["issues"])
            return data
        else:
            return None


# 减少重放过程中显示的会话问题数量，以优化用户体验。
# 参数：
# - issues_list: 包含会话问题的列表。
# 返回值：
# - issues_list: 经过优化后的会话问题列表。
# To reduce the number of issues in the replay;
# will be removed once we agree on how to show issues
def reduce_issues(issues_list):
    if issues_list is None:
        return None
    i = 0
    # remove same-type issues if the time between them is <2s
    while i < len(issues_list) - 1:
        for j in range(i + 1, len(issues_list)):
            if issues_list[i]["type"] == issues_list[j]["type"]:
                break
        else:
            i += 1
            break

        if issues_list[i]["timestamp"] - issues_list[j]["timestamp"] < 2000:
            issues_list.pop(j)
        else:
            i += 1

    return issues_list
