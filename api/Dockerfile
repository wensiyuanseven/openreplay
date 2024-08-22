FROM python:3.11-alpine
LABEL Maintainer="Rajesh Rajendran<rjshrjndrn@gmail.com>"
LABEL Maintainer="KRAIEM Taha Yassine<tahayk2@gmail.com>"
ARG GIT_SHA
LABEL GIT_SHA=$GIT_SHA

RUN apk add --no-cache build-base tini
ARG envarg
# Add Tini
# Startup daemon
ENV SOURCE_MAP_VERSION=0.7.4 \
    APP_NAME=chalice \
    LISTEN_PORT=8000 \
    PRIVATE_ENDPOINTS=false \
    ENTERPRISE_BUILD=${envarg} \
    GIT_SHA=$GIT_SHA

WORKDIR /work
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . .
RUN mv env.default .env

RUN adduser -u 1001 openreplay -D
USER 1001

ENTRYPOINT ["/sbin/tini", "--"]
CMD ./entrypoint.sh




# 这个Dockerfile是用于构建基于Python 3.11 Alpine的API服务容器镜像。下面是各部分的详细说明：

# ### 1. **基础镜像**
# ```dockerfile
# FROM python:3.11-alpine
# ```
# 使用的是Alpine版本的Python 3.11作为基础镜像。Alpine是轻量级的Linux发行版，非常适合用作Docker基础镜像。

# ### 2. **标签信息**
# ```dockerfile
# LABEL Maintainer="Rajesh Rajendran<rjshrjndrn@gmail.com>"
# LABEL Maintainer="KRAIEM Taha Yassine<tahayk2@gmail.com>"
# ARG GIT_SHA
# LABEL GIT_SHA=$GIT_SHA
# ```
# - `LABEL` 用于给镜像添加元数据。这里定义了两个维护者信息以及`GIT_SHA`标签，后者用于标记当前构建镜像所使用的Git版本（Git commit SHA）。

# ### 3. **安装基础工具**
# ```dockerfile
# RUN apk add --no-cache build-base tini
# ```
# - `apk add` 是Alpine的包管理器命令，`--no-cache` 选项用于避免缓存下载的包，减少镜像大小。
# - `build-base` 是构建工具集，用于编译和构建C/C++库。
# - `tini` 是一个轻量级的init进程，能够帮助处理进程信号，避免一些容器在关闭时遇到的进程孤儿问题。

# ### 4. **环境变量**
# ```dockerfile
# ENV SOURCE_MAP_VERSION=0.7.4 \
#     APP_NAME=chalice \
#     LISTEN_PORT=8000 \
#     PRIVATE_ENDPOINTS=false \
#     ENTERPRISE_BUILD=${envarg} \
#     GIT_SHA=$GIT_SHA
# ```
# - 定义了一组环境变量：
#   - `SOURCE_MAP_VERSION`: 表示源映射版本。
#   - `APP_NAME`: 应用的名称。
#   - `LISTEN_PORT`: 应用监听的端口（默认为8000）。
#   - `PRIVATE_ENDPOINTS`: 用于定义是否使用私有端点。
#   - `ENTERPRISE_BUILD`: 传递构建参数`envarg`，表示是否为企业版构建。
#   - `GIT_SHA`: 构建时传递的Git提交ID，用于追踪当前镜像对应的代码版本。

# ### 5. **工作目录**
# ```dockerfile
# WORKDIR /work
# ```
# - 设置工作目录为`/work`，所有后续的命令都会在这个目录下执行。

# ### 6. **安装Python依赖**
# ```dockerfile
# COPY requirements.txt ./requirements.txt
# RUN pip install --no-cache-dir --upgrade -r requirements.txt
# ```
# - 将本地的`requirements.txt`文件复制到工作目录下。
# - 使用`pip`安装项目依赖，`--no-cache-dir`选项用来避免缓存安装的包文件，减少镜像大小。

# ### 7. **复制项目文件**
# ```dockerfile
# COPY . .
# RUN mv env.default .env
# ```
# - 将所有项目文件复制到容器中。
# - 将`env.default`文件重命名为`.env`，用于应用的环境配置。

# ### 8. **创建用户并切换到非root用户**
# ```dockerfile
# RUN adduser -u 1001 openreplay -D
# USER 1001
# ```
# - 创建一个名为`openreplay`的用户，UID为1001。
# - 切换到非root用户`openreplay`以增强容器安全性。

# ### 9. **定义启动命令**
# ```dockerfile
# ENTRYPOINT ["/sbin/tini", "--"]
# CMD ./entrypoint.sh
# ```
# - 使用`/sbin/tini`作为`ENTRYPOINT`，以确保容器能够正确处理信号。
# - 定义`CMD`命令为运行`./entrypoint.sh`，表示容器启动时执行该脚本。

# ### 总结

# 这个Dockerfile用于构建一个基于Python 3.11的容器化API应用，使用Alpine作为基础镜像以确保轻量化。它包含了安装依赖、环境变量配置、用户安全性等步骤，并且使用`tini`来处理进程信号，确保容器的稳定运行。