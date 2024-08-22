#!/bin/bash

DOTENV_FILE=./.env
if [ -f "$DOTENV_FILE" ]; then
    echo "$DOTENV_FILE exists, nothing to do."
else
  cp env.dev $DOTENV_FILE
  echo "$DOTENV_FILE was created, please fill the missing required values."
fi



# 这个 Bash 脚本的作用是检查当前目录下是否存在 `.env` 文件。如果文件存在，它会输出一条消息表示文件已经存在，不需要进行任何操作。如果文件不存在，它会从 `env.dev` 文件中复制一份新的 `.env` 文件，并提醒用户填写缺少的必要值。

# ### 具体步骤解释：
# 1. `DOTENV_FILE=./.env`: 定义一个变量 `DOTENV_FILE`，表示目标 `.env` 文件的路径。
   
# 2. `if [ -f "$DOTENV_FILE" ]; then`: 使用 `if` 判断条件 `[ -f "$DOTENV_FILE" ]`，这会检查 `.env` 文件是否存在。
#    - 如果文件存在，则执行 `then` 代码块中的内容。
   
# 3. `echo "$DOTENV_FILE exists, nothing to do."`: 如果 `.env` 文件存在，输出一条提示信息，表示文件已经存在，不需要做其他操作。

# 4. `else`: 如果文件不存在，则执行 `else` 部分的代码。

# 5. `cp env.dev $DOTENV_FILE`: 将 `env.dev` 文件复制为 `.env` 文件。

# 6. `echo "$DOTENV_FILE was created, please fill the missing required values."`: 输出一条信息提醒用户已经创建了 `.env` 文件，并请用户填写必要的缺少值。

# ### 总结：
# - **如果 `.env` 文件已经存在**，脚本将输出一条提示，并结束操作。
# - **如果 `.env` 文件不存在**，脚本将从 `env.dev` 文件复制创建 `.env`，并提醒用户检查文件内容，填写必要的值。