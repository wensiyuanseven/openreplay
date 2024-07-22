import asyncio
from contextlib import asynccontextmanager


@asynccontextmanager
async def async_resource():
    # 1. 进入上下文时执行的代码
    print("获取资源")
    await asyncio.sleep(1)  # 模拟异步资源获取
    resource = "资源"
    try:
        # 2. yield 语句将资源提供给上下文块
        yield resource
    finally:
        # 3. 退出上下文时执行的代码
        print("释放资源")
        await asyncio.sleep(1)  # 模拟异步资源释放


async def main():
    async with async_resource() as res:
        print(f"使用 {res}")

# 运行异步主函数
asyncio.run(main())
