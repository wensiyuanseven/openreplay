# 这段代码实现了一个多线程环境下与 PostgreSQL 数据库交互的管理系统，包含了连接池管理、数据库连接生命周期管理、查询执行以及连接池的自动重试机制。
# 通过这一套封装，代码能够高效且安全地处理多个线程对数据库的并发访问，同时提供了对连接的生命周期管理和日志记录，方便调试和维护。
import logging
import time
from threading import Semaphore  # 用 Semaphore:信号 控制同时访问资源的最大线程数，确保多线程环境下的连接安全。
import psycopg2
import psycopg2.extras
from decouple import config
from psycopg2 import pool

# 如果一个 Python 文件（模块）被直接运行，那么 __name__ 的值会被设置为 "__main__"
# 如果一个 Python 文件被导入到其他文件中作为模块使用，那么 __name__ 的值会被设置为该模块的名字（通常是文件名，不包括扩展名 .py）。
logger = logging.getLogger(__name__)

# Python 字典，用于存储 PostgreSQL 数据库连接的配置信息。
_PG_CONFIG = {
    "host": config("pg_host"),
    "database": config("pg_dbname"),
    "user": config("pg_user"),
    "password": config("pg_password"),
    "port": config("pg_port", cast=int),
    "application_name": config("APP_NAME", default="PY"),  # 用于标识与数据库建立的连接的名称
}
# 复制 _PG_CONFIG 字典的内容到 PG_CONFIG 字典  防止某些场景中 _PG_CONFIG 被修改时影响到 PG_CONFIG
PG_CONFIG = dict(_PG_CONFIG)
# 如果 PG_TIMEOUT 的值大于 0，则表示设置了一个有效的超时时间，因此需要配置数据库连接的超时选项。
if config("PG_TIMEOUT", cast=int, default=0) > 0:
    # f"" 是 Python 3.6 引入的一种字符串格式化语法，称为 f-string（格式化字符串字面量）。它允许你在字符串中直接插入表达式的值，类似于模板字符串
    # 设置超时 statement_timeout用于设置 SQL 语句的超时时间。如果查询超过这个时间，PostgreSQL 将自动终止该查询
    # PostgreSQL 特定的配置参数。这个配置只对当前的会话有效，不会影响到其他会话或全局配置。 -c 指定了一个临时的会话级别的配置参数 statement_timeout
    # -c 指定了一个临时的会话级别的配置参数 statement_timeout
    PG_CONFIG["options"] = f"-c statement_timeout={config('PG_TIMEOUT', cast=int) * 1000}"


# psycopg2.pool.ThreadedConnectionPool 是一个强大的工具，用于管理与 PostgreSQL 数据库的多线程连接池。
# 它可以显著提高应用程序的性能，特别是在需要处理大量并发数据库请求的场景中。通过连接池，应用程序可以更高效地复用数据库连接，减少连接创建和销毁的开销。
# 实现了一个自定义的连接池类 ，用于管理 PostgreSQL 数据库连接池。
class ORThreadedConnectionPool(psycopg2.pool.ThreadedConnectionPool):
    def __init__(self, minconn, maxconn, *args, **kwargs):
        # 信号量的初始值（即可同时访问资源的最大线程数）。 默认值为1时，表示这个信号量相当于一个互斥锁（只允许一个线程访问资源）。
        self._semaphore = Semaphore(maxconn)
        super().__init__(minconn, maxconn, *args, **kwargs)

    def getconn(self, *args, **kwargs):
        # 减少信号量的计数器。如果计数器大于零，允许线程继续执行；否则，线程会被阻塞，直到其他线程释放资源。
        self._semaphore.acquire()
        try:
            # 使用 getconn() 方法从连接池中获取一个连接。这个连接可以用于执行 SQL 查询。
            return super().getconn(*args, **kwargs)
        except psycopg2.pool.PoolError as e:
            if str(e) == "connection pool is closed":
                make_pool()
            raise e

    def putconn(self, *args, **kwargs):
        try:
            super().putconn(*args, **kwargs)
            # 增加信号量的计数器，并释放资源。如果有任何线程被阻塞，调用 release() 会唤醒其中一个线程。
            self._semaphore.release()
        except psycopg2.pool.PoolError as e:
            if str(e) == "trying to put unkeyed connection":
                logger.warning("!!! 尝试建立非密钥连接")
                logger.warning(f"env-PG_POOL:{config('PG_POOL', default=None)}")
                return
            raise e


# 冒号后面是类型注解
# 尽管类型注解声明了 postgreSQL_pool 应该是 ThreadedConnectionPool 类型，
# 但赋值为 None 是有效的，因为 None 是一种特殊的值，表示“无”或“空”
postgreSQL_pool: ORThreadedConnectionPool = None

RETRY_MAX = config("PG_RETRY_MAX", cast=int, default=50)
RETRY_INTERVAL = config("PG_RETRY_INTERVAL", cast=int, default=2)
RETRY = 0  # 重试


# 连接池创建: make_pool 函数负责根据配置创建并初始化连接池。
# 自动重试: 如果连接池创建失败，函数会根据设定的重试次数和间隔时间重新尝试连接。
def make_pool():
    # not 运算符用于取反 如果是false  return
    if not config("PG_POOL", cast=bool, default=True):
        return
    # 使用全局变量
    global postgreSQL_pool
    global RETRY
    if postgreSQL_pool is not None:
        try:
            postgreSQL_pool.closeall()  # 关闭连接池中的所有连接。
        except (Exception, psycopg2.DatabaseError) as error:
            logging.error("关闭与 PostgreSQL 的所有连接时出错", error)
    try:
        # 赋值 实例化class
        postgreSQL_pool = ORThreadedConnectionPool(config("PG_MINCONN", cast=int, default=4), config("PG_MAXCONN", cast=int, default=8), **PG_CONFIG)
        if postgreSQL_pool:
            logging.info("连接池创建成功!")
            # DatabaseError是 psycopg2 库中特定的异常类型，用于捕获与 PostgreSQL 数据库相关的错误。
    except (Exception, psycopg2.DatabaseError) as error:
        logging.error("连接到 PostgreSQL 时出错", error)
        if RETRY < RETRY_MAX:
            RETRY += 1
            logging.info(f"等待 {RETRY_INTERVAL}s 之前 重试 n°{RETRY}")
            # 重试
            time.sleep(RETRY_INTERVAL)
            make_pool()
        else:
            raise error


# 数据库客户端类 PostgresClient
# 管理数据库连接: 这个类封装了数据库连接的管理，包括通过连接池获取连接，执行查询，以及处理长查询和无限制查询的特殊配置。
# 上下文管理: 通过 __enter__ 和 __exit__ 方法实现了上下文管理协议，方便使用 with 语句来自动管理数据库连接的生命周期。
# __enter__, __exit__, 和 __execute__ 是 Python 特殊方法（或魔术方法），
class PostgresClient:
    connection = None
    cursor = None
    long_query = False  # 长链接
    unlimited_query = False  # 无限制查询

    def __init__(self, long_query=False, unlimited_query=False, use_pool=True):
        self.long_query = long_query
        self.unlimited_query = unlimited_query
        self.use_pool = use_pool
        if unlimited_query:
            long_config = dict(_PG_CONFIG)
            long_config["application_name"] += "-UNLIMITED"
            self.connection = psycopg2.connect(**long_config)
        elif long_query:
            long_config = dict(_PG_CONFIG)
            long_config["application_name"] += "-LONG"
            long_config["options"] = f"-c statement_timeout=" f"{config('pg_long_timeout', cast=int, default=5 * 60) * 1000}"
            self.connection = psycopg2.connect(**long_config)
        elif not use_pool or not config("PG_POOL", cast=bool, default=True):
            single_config = dict(_PG_CONFIG)
            single_config["application_name"] += "-NOPOOL"
            single_config["options"] = f"-c statement_timeout={config('PG_TIMEOUT', cast=int, default=30) * 1000}"
            self.connection = psycopg2.connect(**single_config)
        else:
            self.connection = postgreSQL_pool.getconn()  # 使用 getconn() 方法从连接池中获取一个连接。这个连接可以用于执行 SQL 查询。

    def __enter__(self):
        if self.cursor is None:
            # 创建了一个游标对象（cursor），用于执行数据库查询并处理结果集 创建了一个使用 RealDictCursor 作为游标工厂的游标，这意味着查询结果将以字典的形式返回，而不是默认的元组形式
            # 这是 psycopg2 库中用于创建游标的方法。
            # 游标是数据库操作中的一个重要概念，表示数据库中的一个工作区域，通过游标你可以执行 SQL 语句（如 SELECT、INSERT、UPDATE 等），并获取查询的结果
            # self.connection 是一个数据库连接对象，表示与 PostgreSQL 数据库的连接。通过调用 self.connection.cursor()，你可以创建一个与该连接关联的游标。
            # cursor_factory 是 cursor() 方法的一个可选参数，用于指定游标工厂，决定游标如何生成和返回查询结果。
            # psycopg2.extras.RealDictCursor 是 psycopg2 库中提供的一种特殊游标类型，它返回的每一行结果都是一个字典，其中列名作为字典的键，对应的列值作为字典的值。
            # 与默认的游标不同，默认游标返回的是元组格式的数据，而 RealDictCursor 返回的是字典格式，这使得访问结果中的字段更加直观和方便，特别是在你需要根据列名来处理数据时。
            self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            self.cursor.cursor_execute = self.cursor.execute
            self.cursor.execute = self.__execute
            self.cursor.recreate = self.recreate_cursor
        return self.cursor

    def __exit__(self, *args):
        try:
            self.connection.commit()
            self.cursor.close()
            if not self.use_pool or self.long_query or self.unlimited_query:
                self.connection.close()
        except Exception as error:
            logging.error("提交/关闭 PG 连接时出错", error)
            if str(error) == "connection already closed" and self.use_pool and not self.long_query and not self.unlimited_query and config("PG_POOL", cast=bool, default=True):
                logging.info("重新创建连接池")
                make_pool()
            else:
                raise error
        finally:
            if config("PG_POOL", cast=bool, default=True) and self.use_pool and not self.long_query and not self.unlimited_query:
                # 释放连接
                postgreSQL_pool.putconn(self.connection)

    # __execute 方法是自定义的方法
    # 外部受保护
    # 如果一个类的属性或方法名称以双下划线开头，并且不以双下划线结尾，例如 __execute，Python 会对其名称进行“名称改写”（Name Mangling），将其改写为 _ClassName__methodName 的形式，以避免名称冲突。
    def __execute(self, query, vars=None):
        try:
            result = self.cursor.cursor_execute(query=query, vars=vars)
        except psycopg2.Error as error:
            logging.error(f"!!! 错误类型:{type(error)} 执行查询时: ")
            logging.error(query)
            logging.info("开始回滚以允许将来执行")
            # 执行事务回滚操作的一个方法调用。它用于撤销当前事务中已经执行的所有更改，并将数据库状态恢复到事务开始时的状态
            self.connection.rollback()
            raise error
        return result

    def recreate_cursor(self, rollback=False):
        if rollback:
            try:
                self.connection.rollback()
            except Exception as error:
                logging.error("回滚连接以进行重新创建时出错", error)
        try:
            self.cursor.close()
        except Exception as error:
            logging.error("关闭游标进行重新创建时出错", error)
        self.cursor = None
        return self.__enter__()


# 异步初始化: init 函数在程序启动时异步创建连接池。
async def init():
    logging.info(f">连接池init:{config('PG_POOL', default=None)}")
    # 默认是true
    if config("PG_POOL", cast=bool, default=True):
        # 制作池
        make_pool()


# 异步终止: terminate 函数在程序结束时关闭所有与 PostgreSQL 数据库的连接。
async def terminate():
    global postgreSQL_pool
    if postgreSQL_pool is not None:
        try:
            postgreSQL_pool.closeall()
            logging.info("关闭所有与 PostgreSQL 的连接")
        except (Exception, psycopg2.DatabaseError) as error:
            logging.error("关闭与 PostgreSQL 的所有连接时出错", error)
