# CronTrigger 触发器允许你使用类 cron 表达式来调度任务。它可以精确地控制任务在特定时间点运行
# 当你需要在特定的时间、日期、周几或月份等周期性触发任务时，使用 CronTrigger 是非常合适的。
from apscheduler.triggers.cron import CronTrigger

# IntervalTrigger 触发器基于固定的时间间隔来调度任务。它更适合需要每隔一段时间重复执行的任务。
from apscheduler.triggers.interval import IntervalTrigger

from chalicelib.core import telemetry
from chalicelib.core import weekly_report, jobs, health


async def run_scheduled_jobs() -> None:
    # 获取所有已调度的任务并逐个执行。对于删除用户数据的任务，它会删除与用户相关的会话记录，并更新任务的状态。
    jobs.execute_jobs()


async def weekly_report_cron() -> None:
    # 生成每周报告并通过电子邮件发送给用户。这个函数是任务调度程序（cron job）的核心部分，通常定期运行，例如每周一次。
    weekly_report.cron()


async def telemetry_cron() -> None:
    telemetry.compute()
    #  用于定期更新并发送租户的统计数据。


# 会去跑这些定时任务
async def health_cron() -> None:
    # 执行健康检查
    health.cron()


async def weekly_health_cron() -> None:
    # 每周执行健康检查
    health.weekly_cron()


# cron 计划任务
# CronTrigger：用于基于时间的调度，适合在特定时间点触发任务。
# IntervalTrigger：用于基于时间间隔的调度，适合定期重复执行的任务。
# day_of_week="*" 则表示每周的每一天都执行任务。
# day_of_week="*", hour=0, minute=15 使其在每天的凌晨 0:15（也就是午夜过后15分钟）运行。因为 day_of_week="*"，所以任务会每天执行，无论是工作日还是周末。
# CronTrigger 使其在每周日的凌晨 5:00 运行
# IntervalTrigger(hours=0, minutes=30, start_date="2023-04-01 0:0:0", jitter=300)
# hours=0, minutes=30：表示任务应每隔 30 分钟执行一次。IntervalTrigger 允许你设置任务在固定的时间间隔内重复执行。
# start_date="2023-04-01 0:0:0"：表示任务的开始时间是 2023 年 4 月 1 日 00:00:00。任务将从这个时间开始执行，并每隔 30 分钟重复执行。
#TODO
#  misfire_grace_time：
# 解释：
# misfire_grace_time 参数指定任务错过预定执行时间后的最大容忍时间（以秒为单位）。如果任务未能在预定的时间点执行，并且在这个时间范围内启动，该任务仍会被执行。如果超出了这个时间范围，任务将被跳过，不会执行。
# 用途：
# 这个参数用于处理任务调度中的延迟问题。尤其是在使用 AsyncIOScheduler 时，系统负载、事件循环的阻塞或其他延迟可能会导致任务不能在预定时间点执行。misfire_grace_time 允许你定义一个宽限期，在这个时间内，任务如果能够启动仍会被执行。
# 如果你的任务时间敏感（例如，必须在指定时间点执行），你可以设置一个较短的 misfire_grace_time。对于不那么严格的任务，可以设置较长的宽限期。
# 示例：
# misfire_grace_time=300 表示如果任务错过了预定时间，只要在5分钟内能够执行，它就会被执行。超过5分钟，任务将被跳过。
#TODO
# max_instances：
# 解释：

# max_instances 参数控制同一个任务在同一时间可以运行的最大实例数量。即使任务被调度多次，max_instances 限制了任务的并发执行数量。如果达到最大实例数，新的任务实例将不会启动，直到现有的实例完成。
# 用途：

# 在使用 AsyncIOScheduler 时，任务可能是异步的，如果任务执行时间较长，而调度器又触发了多个任务实例，则会出现并发执行的情况。max_instances 用于防止同一任务的多个实例在同一时间并发运行，这对于依赖共享资源或不希望并发运行的任务特别重要。
# 如果任务可以并发执行，可以设置 max_instances 为大于 1 的值。如果任务不能并发执行（例如，写入同一个文件或访问共享资源），则应将 max_instances 设置为 1。
# 示例：
# max_instances=1 表示在任何时间点，最多只允许一个实例在运行。如果任务正在执行，而新的调度周期到了，则新的实例将不会启动，直到现有实例完成。
# max_instances=2 表示最多允许两个实例同时运行。超出这个数量，新的任务实例将被推迟。
# TODO
# jitter=300：表示任务的执行时间会随机浮动最多 300 秒（5 分钟）。这可以用于防止任务在大规模部署时同时触发，从而减轻服务器负载或避免资源争夺。
cron_jobs = [
    {"func": telemetry_cron, "trigger": CronTrigger(day_of_week="*"), "misfire_grace_time": 60 * 60, "max_instances": 1},
    {"func": run_scheduled_jobs, "trigger": CronTrigger(day_of_week="*", hour=0, minute=15), "misfire_grace_time": 20, "max_instances": 1},
    {"func": weekly_report_cron, "trigger": CronTrigger(day_of_week="mon", hour=5), "misfire_grace_time": 60 * 60, "max_instances": 1},
    {"func": health_cron, "trigger": IntervalTrigger(hours=0, minutes=30, start_date="2023-04-01 0:0:0", jitter=300), "misfire_grace_time": 60 * 60, "max_instances": 1},
    {"func": weekly_health_cron, "trigger": CronTrigger(day_of_week="sun", hour=5), "misfire_grace_time": 60 * 60, "max_instances": 1},
]
