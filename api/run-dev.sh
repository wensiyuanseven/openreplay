#!/bin/zsh
# 注意：必须先启动虚拟环境哦
uvicorn app:app --reload --log-level ${S_LOGLEVEL:-warning}