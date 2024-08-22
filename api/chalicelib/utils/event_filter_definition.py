# 该代码片段定义了两个类：Event 和 SupportedFilter。Event 类用于描述一个与用户界面交互相关的事件，包含了用户界面类型、数据库表和列的信息。
# 而 SupportedFilter 类则用于描述一个支持的过滤器，它包含了用于获取数据和查询数据的方法或属性。这两个类可用于处理用户界面的事件和数据过滤操作。


# 定义一个与用户界面交互相关的事件类。
# 该类用于存储与用户界面事件相关的信息，如用户界面类型、数据库表名和列名。

# 初始化Event类的实例。
# 参数：
# - ui_type: 用户界面类型，类型为字符串（str），表示触发事件的UI元素类型。
# - table: 数据库表名，类型为字符串（str），表示与事件相关的数据表。
# - column: 数据库列名，类型为字符串（str），表示与事件相关的数据列。
class Event:
    def __init__(self, ui_type, table, column):
        self.ui_type = ui_type  # 用户界面类型
        self.table = table  # 数据库表名
        self.column = column  # 数据库列名

# 定义一个支持的数据过滤器类。
# 该类用于存储与数据过滤相关的方法或属性，如获取数据和查询数据的方法或属性。

class SupportedFilter:
     # 初始化SupportedFilter类的实例。
    # 参数：
    # - get: 获取数据的方法或属性，类型为函数或其他可调用对象，表示用于获取数据的方式。
    # - query: 查询数据的方法或属性，类型为函数或其他可调用对象，表示用于查询数据的方式。
    def __init__(self, get, query):
        self.get = get  #获取数据的方法或属性
        self.query = query # 查询数据的方法或属性
