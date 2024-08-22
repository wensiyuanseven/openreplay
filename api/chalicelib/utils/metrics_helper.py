# 该函数用于计算时间范围内的步长大小（step_size），以便根据给定的密度和其他参数划分时间区间。函数可以返回整数类型的步长，也可以返回浮点数类型的步长，具体取决于 decimal 参数的值。
# 计算时间范围内的步长大小（step_size）。
# 该函数根据起始和结束时间戳、给定的密度和可选参数，计算并返回步长大小。
# 参数：
# - startTimestamp: 整型（int），表示起始时间戳。
# - endTimestamp: 整型（int），表示结束时间戳。
# - density: 整型（int），表示密度，用于决定将时间区间划分为多少个步长。
# - decimal: 布尔型（bool），可选参数，默认为 False。如果为 True，则返回浮点数类型的步长；如果为 False，则返回整数类型的步长。
# - factor: 整型（int），可选参数，默认为 1000，用于缩小时间戳的单位，例如将时间戳从毫秒转换为秒。
# 返回值：
# - step_size: 根据给定参数计算出的步长大小，类型为整数或浮点数。


def __get_step_size(startTimestamp, endTimestamp, density, decimal=False, factor=1000):
    step_size = endTimestamp // factor - startTimestamp // factor
    if decimal:
        return step_size / density
    return step_size // (density - 1)
