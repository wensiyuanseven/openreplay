#!/bin/zsh
# uvicorn app_alerts:app：这个命令启动的是 app_alerts.py 模块中的 app 实例。
uvicorn app_alerts:app --reload --port 8888 --log-level ${S_LOGLEVEL:-warning}