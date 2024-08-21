# 这段代码定义了一个函数 get_status，用于返回系统的当前状态信息。包括当前是否有激活的计划（如订阅计划）、系统的版本（EDITION），以及计划的过期日期。
EDITION = "foss"


# 函数：get_status
# 功能：获取系统的状态信息，包括是否有激活的计划、系统版本和计划过期日期。
# 参数：
# - tenant_id: 租户ID（可选），默认为 None。
# 返回值：
# - 返回一个字典，包含系统状态信息：
#   - "hasActivePlan": 是否有激活的计划，默认为 True。
#   - "edition": 当前系统的版本，使用全局变量 EDITION。
#   - "expirationDate": 计划的过期日期，默认为 -1，表示没有过期日期或无限期。
def get_status(tenant_id=None):
    return {"hasActivePlan": True, "edition": EDITION, "expirationDate": -1}
