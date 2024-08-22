#!/bin/bash

# Script to build crons module
# flags to accept:
# envarg: build for enterprise edition.
# Default will be OSS build.

# Usage: IMAGE_TAG=latest DOCKER_REPO=myDockerHubID bash build.sh <ee>

git_sha1=${IMAGE_TAG:-$(git rev-parse HEAD)}
envarg="default-foss"
source ../scripts/lib/_docker.sh
check_prereq() {
    which docker || {
        echo "Docker not installed, please install docker."
        exit=1
    }
    [[ exit -eq 1 ]] && exit 1
}

function build_crons() {
    destination="_crons_ee"
    cp -R ../api ../${destination}
    cd ../${destination}
    tag=""
    # Copy enterprise code

    cp -rf ../ee/api/* ./
    envarg="default-ee"
    tag="ee-"
    mv Dockerfile_crons.dockerignore .dockerignore
    docker build -f ./Dockerfile_crons --platform=linux/${ARCH:-'amd64'} --build-arg envarg=$envarg -t ${DOCKER_REPO:-'local'}/crons:${git_sha1} .
    cd ../api
    rm -rf ../${destination}
    [[ $PUSH_IMAGE -eq 1 ]] && {
        docker push ${DOCKER_REPO:-'local'}/crons:${git_sha1}
        docker tag ${DOCKER_REPO:-'local'}/crons:${git_sha1} ${DOCKER_REPO:-'local'}/crons:${tag}latest
        docker push ${DOCKER_REPO:-'local'}/crons:${tag}latest
    }
    [[ $SIGN_IMAGE -eq 1 ]] && {
        cosign sign --key $SIGN_KEY ${DOCKER_REPO:-'local'}/crons:${git_sha1}
    }
    echo "completed crons build"
}

check_prereq
[[ $1 == "ee" ]] && {
    build_crons $1
} || {
    echo -e "Crons is only for ee. Rerun the script using \n bash $0 ee"
    exit 100
}



# ### Bash 脚本作用

# 该脚本用于构建 `crons` 模块的企业版 Docker 镜像 (Enterprise Edition, `ee`)。默认情况下，只有企业版可供构建。开源版 (OSS) 不适用此脚本。它还支持将生成的 Docker 镜像推送到指定的 Docker registry，并支持对镜像进行签名。

# ### 脚本详细说明

# 1. **环境变量**:
#    - `IMAGE_TAG`：Docker 镜像的标签，默认为当前的 Git 提交哈希值（完整的 `git_sha1`）。
#    - `DOCKER_REPO`：Docker 镜像推送的目标仓库，默认为 `local`。
#    - `PUSH_IMAGE`：如果设置为 `1`，则将镜像推送到 Docker registry。
#    - `SIGN_IMAGE`：如果设置为 `1`，则使用 `cosign` 对镜像进行签名。
#    - `SIGN_KEY`：用于签名镜像的密钥路径。

# 2. **主要功能**:
#    - 检查 Docker 是否已安装。
#    - 仅构建企业版 (`ee`) 的 `crons` 模块。
#    - 构建 Docker 镜像并根据需要推送到 Docker registry。
#    - 如果指定，则对生成的 Docker 镜像进行签名。

# ### 关键步骤与解释

# 1. **检查 Docker 是否安装 (`check_prereq`)**:
#    该函数通过 `which docker` 检查 Docker 是否安装。如果没有安装 Docker，脚本会提示用户安装，并退出。

# 2. **构建镜像 (`build_crons`)**:
#    - 创建一个 `_crons_ee` 目录并将 `../api` 目录中的文件复制到该目录。
#    - 从 `../ee/api/` 目录中复制企业版的特定代码到 `_crons_ee`。
#    - 使用 `Dockerfile_crons` 构建 `crons` 的企业版 Docker 镜像。构建过程中指定了 `envarg` 为 `default-ee`，以区分企业版构建。
#    - 构建完成后，会删除临时生成的 `_crons_ee` 目录。
#    - 如果 `PUSH_IMAGE=1`，则将镜像推送到 Docker registry，同时标记 `latest` 版本并推送。
#    - 如果 `SIGN_IMAGE=1`，则使用 `cosign` 对镜像进行签名。

# 3. **控制流程**:
#    - 脚本检查传入的参数，如果第一个参数是 `ee`，则执行 `build_crons` 函数，否则提示用户重新运行脚本并退出。

# ### 参数和环境变量

# - **`IMAGE_TAG`**：用于指定 Docker 镜像的标签。如果未指定，则使用当前 Git 提交的哈希值。
# - **`DOCKER_REPO`**：Docker 镜像推送的目标仓库，默认为 `local`。
# - **`PUSH_IMAGE`**：如果设置为 `1`，镜像会被推送到 Docker registry。
# - **`SIGN_IMAGE`**：如果设置为 `1`，使用 `cosign` 对镜像进行签名。
# - **`SIGN_KEY`**：用于镜像签名的密钥路径。

# ### 使用示例

# 1. **构建并推送 `crons` 企业版镜像**:
#    ```bash
#    IMAGE_TAG=latest DOCKER_REPO=myDockerHubID PUSH_IMAGE=1 bash build.sh ee
#    ```

# 2. **构建并签名企业版镜像**:
#    ```bash
#    IMAGE_TAG=latest DOCKER_REPO=myDockerHubID SIGN_IMAGE=1 SIGN_KEY=path/to/key bash build.sh ee
#    ```

# ### 总结

# 该脚本专门用于构建 `crons` 模块的企业版镜像，并提供了镜像推送和签名的选项。脚本的逻辑确保只有 `ee` 版本可以构建，并且通过传入环境变量来灵活控制镜像的构建、推送和签名。