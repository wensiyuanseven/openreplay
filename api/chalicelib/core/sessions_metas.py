import schemas
from chalicelib.core import autocomplete
from chalicelib.utils.event_filter_definition import SupportedFilter
# 这段代码的主要功能是基于不同的 FilterType（过滤类型）对元数据进行自动补全搜索（autocomplete）。用户可以通过指定过滤类型和文本关键字进行搜索，系统会根据预定义的支持类型，返回相关的自动补全结果。

# SUPPORTED_TYPES:
# 作用: 定义了一组支持的过滤类型（FilterType），并为每种过滤类型配置了获取和查询操作。这些操作通过调用 autocomplete.__generic_autocomplete_metas 函数来实现。
# search 函数:
# 作用: 执行自动补全搜索操作。根据提供的 meta_type（过滤类型）和 text（搜索文本），在 SUPPORTED_TYPES 中查找并执行相应的获取操作，最终返回搜索结果。
SUPPORTED_TYPES = {
    schemas.FilterType.user_os: SupportedFilter(
        get=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_os),
        query=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_os)),
    schemas.FilterType.user_browser: SupportedFilter(
        get=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_browser),
        query=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_browser)),
    schemas.FilterType.user_device: SupportedFilter(
        get=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_device),
        query=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_device)),
    schemas.FilterType.user_country: SupportedFilter(
        get=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_country),
        query=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_country)),
    schemas.FilterType.user_city: SupportedFilter(
        get=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_city),
        query=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_city)),
    schemas.FilterType.user_state: SupportedFilter(
        get=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_state),
        query=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_state)),
    schemas.FilterType.user_id: SupportedFilter(
        get=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_id),
        query=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_id)),
    schemas.FilterType.user_anonymous_id: SupportedFilter(
        get=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_anonymous_id),
        query=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_anonymous_id)),
    schemas.FilterType.rev_id: SupportedFilter(
        get=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.rev_id),
        query=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.rev_id)),
    schemas.FilterType.referrer: SupportedFilter(
        get=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.referrer),
        query=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.referrer)),
    schemas.FilterType.utm_campaign: SupportedFilter(
        get=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.utm_campaign),
        query=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.utm_campaign)),
    schemas.FilterType.utm_medium: SupportedFilter(
        get=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.utm_medium),
        query=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.utm_medium)),
    schemas.FilterType.utm_source: SupportedFilter(
        get=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.utm_source),
        query=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.utm_source)),
    # IOS
    schemas.FilterType.user_os_mobile: SupportedFilter(
        get=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_os_mobile),
        query=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_os_mobile)),
    schemas.FilterType.user_device_mobile: SupportedFilter(
        get=autocomplete.__generic_autocomplete_metas(
            typename=schemas.FilterType.user_device_mobile),
        query=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_device_mobile)),
    schemas.FilterType.user_country_mobile: SupportedFilter(
        get=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_country_mobile),
        query=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_country_mobile)),
    schemas.FilterType.user_id_mobile: SupportedFilter(
        get=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_id_mobile),
        query=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_id_mobile)),
    schemas.FilterType.user_anonymous_id_mobile: SupportedFilter(
        get=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_anonymous_id_mobile),
        query=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.user_anonymous_id_mobile)),
    schemas.FilterType.rev_id_mobile: SupportedFilter(
        get=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.rev_id_mobile),
        query=autocomplete.__generic_autocomplete_metas(typename=schemas.FilterType.rev_id_mobile)),

}

# 功能描述：
# 执行元数据的自动补全搜索操作，根据用户提供的文本和过滤类型，从预定义的支持类型中查找相关结果。

# 参数：
# text: str - 用户输入的搜索关键字。
# meta_type: schemas.FilterType - 指定的过滤类型，用于选择特定的自动补全逻辑。
# project_id: int - 项目ID，用于在特定项目上下文中执行搜索。
# 返回值：
# dict:
# data: 包含搜索结果的列表。
# errors: 如果过滤类型不受支持，则返回包含错误信息的列表。
def search(text: str, meta_type: schemas.FilterType, project_id: int):
    rows = []
    if meta_type not in list(SUPPORTED_TYPES.keys()):
        return {"errors": ["unsupported type"]}
    rows += SUPPORTED_TYPES[meta_type].get(project_id=project_id, text=text)
    # for IOS events autocomplete
    # if meta_type + "_IOS" in list(SUPPORTED_TYPES.keys()):
    #     rows += SUPPORTED_TYPES[meta_type + "_IOS"].get(project_id=project_id, text=text)
    return {"data": rows}
