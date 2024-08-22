# 这段代码定义了一个装饰器 timed，用于计算和记录被装饰函数的执行时间，并将其记录到日志中。此装饰器特别适用于调试和性能分析。
from functools import wraps
from time import time
import inspect
from chalicelib.utils import helper
import logging

logger = logging.getLogger(__name__)

# 功能描述:
# 这个装饰器主要用于测量被装饰函数的执行时间。
# 在函数执行之前，记录当前时间。
# 在函数执行结束后，计算函数的执行时长，并记录到日志中。
# 参数说明:

# f: 被装饰的函数。
# 内部逻辑:

# 时间测量: 使用 time() 函数记录函数开始执行的时间，在函数执行结束后计算总耗时。
# 条件检查: 通过 helper.TRACK_TIME 来决定是否需要记录时间。如果 TRACK_TIME 为 False，则直接执行函数而不进行时间测量。
# 日志记录:
# 如果调用栈中的上一级函数是 _view_func，直接记录函数的执行时间。
# 否则，获取调用栈并过滤掉不相关的函数，然后记录调用链和执行时间。
# 返回值:

# 返回被装饰函数的执行结果。
# 应用场景:
# 该装饰器可用于调试、性能分析和优化。通过记录函数的执行时间，可以识别出耗时较长的操作，从而进行针对性优化。
def timed(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        if not helper.TRACK_TIME:
            return f(*args, **kwds)
        start = time()
        result = f(*args, **kwds)
        elapsed = time() - start
        if inspect.stack()[1][3] == "_view_func":
            logging.debug("%s: took %d s to finish" % (f.__name__, elapsed))
        else:
            call_stack = [i[3] for i in inspect.stack()[1:] if i[3] != "wrapper"]
            call_stack = [c for c in call_stack if c not in ["__init__", "__call__", "finish_request", "process_request_thread", "handle_request", "_generic_handle", "handle", "_bootstrap_inner", "run", "_bootstrap", "_main_rest_api_handler", "_user_handler", "_get_view_function_response", "wrapped_event", "handle_one_request", "_global_error_handler", "openreplay_middleware"]]
            logger.debug("%s > %s took %d s to finish" % (" > ".join(call_stack), f.__name__, elapsed))
        return result

    return wrapper
