#!/bin/bash
# 指定脚本使用 Bash 解释器运行。
# 这个脚本是一个 Bash 脚本，用于检查 .env 文件是否存在，如果不存在，则从 env.dev 文件复制一个新的 .env 文件。以下是详细解释：
DOTENV_FILE=./.env
# 检查 .env 文件是否存在
if [ -f "$DOTENV_FILE" ]; then
    echo "$DOTENV_FILE exists, nothing to do."
else
  # 如果 .env 文件不存在，则从 env.dev 复制一个
  cp env.dev $DOTENV_FILE
  echo "$DOTENV_FILE was created, please fill the missing required values."
fi

# 解释
# Shebang (#!/bin/bash)：指定脚本使用 Bash 解释器运行。
# 定义变量 (DOTENV_FILE=./.env)：定义一个变量 DOTENV_FILE，其值为 ./.env。
# 检查文件是否存在 (if [ -f "$DOTENV_FILE" ]; then)：
# -f 用于检查文件是否存在且为常规文件。
# 如果文件存在，输出提示信息 "$DOTENV_FILE exists, nothing to do."。
# 文件不存在时的操作 (else)：
# 使用 cp env.dev $DOTENV_FILE 复制 env.dev 文件到 .env 文件。
# 输出提示信息 "$DOTENV_FILE was created, please fill the missing required values."。
# 这个脚本确保项目中需要的 .env 文件存在，如果不存在，就从开发环境的模板文件 env.dev 创建一个新的 .env 文件，并提醒用户填写缺少的必需值。