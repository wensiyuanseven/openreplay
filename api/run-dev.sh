#!/bin/zsh
# uvicorn app:app：这个命令启动的是 app.py 模块中的 app 实例。 这个命令使用默认端口（通常是 8000）
uvicorn app:app --reload --log-level ${S_LOGLEVEL:-warning}

# 环境变量设置示例

# export S_LOGLEVEL=debug
# ./run.sh