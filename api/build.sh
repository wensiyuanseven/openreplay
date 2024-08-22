#!/bin/bash

# Script to build api module
# flags to accept:
# envarg: build for enterprise edition.
# Default will be OSS build.

# Usage: IMAGE_TAG=latest DOCKER_REPO=myDockerHubID bash build.sh <ee>

# Helper function
exit_err() {
    err_code=$1
    if [[ $err_code != 0 ]]; then
        exit $err_code
    fi
}

source ../scripts/lib/_docker.sh
ARCH=${ARCH:-'amd64'}

environment=$1
git_sha=$(git rev-parse --short HEAD)
image_tag=${IMAGE_TAG:-git_sha}
envarg="default-foss"
chart="chalice"
check_prereq() {
    which docker || {
        echo "Docker not installed, please install docker."
        exit 1
    }
    return
}

[[ $1 == ee ]] && ee=true
[[ $PATCH -eq 1 ]] && {
    image_tag="$(grep -ER ^.ppVersion ../scripts/helmcharts/openreplay/charts/$chart | xargs | awk '{print $2}' | awk -F. -v OFS=. '{$NF += 1 ; print}')"
    [[ $ee == "true" ]] && {
        image_tag="${image_tag}-ee"
    }
}
update_helm_release() {
    [[ $ee == "true" ]] && return
    HELM_TAG="$(grep -iER ^version ../scripts/helmcharts/openreplay/charts/$chart | awk '{print $2}' | awk -F. -v OFS=. '{$NF += 1 ; print}')"
    # Update the chart version
    sed -i "s#^version.*#version: $HELM_TAG# g" ../scripts/helmcharts/openreplay/charts/$chart/Chart.yaml
    # Update image tags
    sed -i "s#ppVersion.*#ppVersion: \"$image_tag\"#g" ../scripts/helmcharts/openreplay/charts/$chart/Chart.yaml
    # Commit the changes
    git add ../scripts/helmcharts/openreplay/charts/$chart/Chart.yaml
    git commit -m "chore(helm): Updating $chart image release"
}

function build_api() {
    destination="_api"
    [[ $1 == "ee" ]] && {
        destination="_api_ee"
    }
    [[ -d ../${destination} ]] && {
        echo "Removing previous build cache"
        rm -rf ../${destination}
    }
    cp -R ../api ../${destination}
    cd ../${destination} || exit_err 100
    tag=""
    # Copy enterprise code
    [[ $1 == "ee" ]] && {
        cp -rf ../ee/api/* ./
        envarg="default-ee"
        tag="ee-"
    }
    mv Dockerfile.dockerignore .dockerignore
    docker build -f ./Dockerfile --platform linux/${ARCH} --build-arg envarg=$envarg --build-arg GIT_SHA=$git_sha -t ${DOCKER_REPO:-'local'}/${IMAGE_NAME:-'chalice'}:${image_tag} .
    cd ../api || exit_err 100
    rm -rf ../${destination}
    [[ $PUSH_IMAGE -eq 1 ]] && {
        docker push ${DOCKER_REPO:-'local'}/${IMAGE_NAME:-'chalice'}:${image_tag}
        docker tag ${DOCKER_REPO:-'local'}/${IMAGE_NAME:-'chalice'}:${image_tag} ${DOCKER_REPO:-'local'}/chalice:${tag}latest
        docker push ${DOCKER_REPO:-'local'}/${IMAGE_NAME:-'chalice'}:${tag}latest
    }
    [[ $SIGN_IMAGE -eq 1 ]] && {
        cosign sign --key $SIGN_KEY ${DOCKER_REPO:-'local'}/${IMAGE_NAME:-'chalice'}:${image_tag}
    }
    echo "api docker build completed"
}

check_prereq
build_api $environment
echo buil_complete
if [[ $PATCH -eq 1 ]]; then
    update_helm_release
fi



# ### Bash 脚本作用

# 该脚本用于构建 `API` 模块的 Docker 镜像，支持构建开源版 (OSS) 和企业版 (EE) 的镜像。它还支持将生成的 Docker 镜像推送到 Docker 仓库，并支持对镜像进行签名。默认情况下，构建 OSS 版本，除非明确指定构建 EE 版本。

# ### 详细说明

# #### 1. **环境变量**

# - `IMAGE_TAG`：Docker 镜像的标签，默认为当前的 Git 提交哈希。
# - `DOCKER_REPO`：Docker 镜像推送的目标仓库，默认为 `local`。
# - `ARCH`：构建镜像的平台架构，默认为 `amd64`。
# - `PUSH_IMAGE`：如果设置为 `1`，则将镜像推送到 Docker 仓库。
# - `SIGN_IMAGE`：如果设置为 `1`，则对生成的 Docker 镜像进行签名。
# - `SIGN_KEY`：用于签名镜像的密钥路径。

# #### 2. **主要功能**

# - **检查 Docker 是否安装 (`check_prereq`)**：通过 `which docker` 检查 Docker 是否已安装。未安装则提示用户安装，并退出脚本。
  
# - **构建 API 镜像 (`build_api`)**：
#   - 创建一个 `_api` 或 `_api_ee` 目录并将 `../api` 目录中的代码复制到该目录。
#   - 如果指定了企业版 (`ee`)，则将企业版代码 (`../ee/api`) 合并到复制的目录中。
#   - 使用 `Dockerfile` 构建 Docker 镜像，构建完成后删除临时创建的目录。
#   - 如果 `PUSH_IMAGE` 设置为 `1`，则推送镜像到指定的 Docker 仓库，并标记为 `latest`。
#   - 如果 `SIGN_IMAGE` 设置为 `1`，则使用 `cosign` 对生成的镜像进行签名。

# - **更新 Helm 图表版本 (`update_helm_release`)**：
#   - 在 Helm 图表文件中更新版本号 (`version`) 以及 Docker 镜像标签 (`ppVersion`)。
#   - 提交更新的 Helm 图表到 Git。

# #### 3. **流程控制**

# - 检查传入参数是否为 `ee`，如果是，则构建企业版 (`ee`) 镜像。否则构建默认的 OSS 版本。
# - 如果设置了 `PATCH` 环境变量，则更新 Helm 图表中的镜像版本号并提交。

# ### 参数和环境变量

# - **`IMAGE_TAG`**：用于指定 Docker 镜像的标签，默认为当前 Git 提交的哈希值。
# - **`DOCKER_REPO`**：Docker 镜像推送的目标仓库，默认为 `local`。
# - **`PUSH_IMAGE`**：如果设置为 `1`，镜像会被推送到 Docker 仓库。
# - **`SIGN_IMAGE`**：如果设置为 `1`，使用 `cosign` 对镜像进行签名。
# - **`SIGN_KEY`**：用于镜像签名的密钥路径。

# ### 使用示例

# 1. **构建并推送 `API` 开源版镜像**：
#    ```bash
#    IMAGE_TAG=latest DOCKER_REPO=myDockerHubID PUSH_IMAGE=1 bash build.sh
#    ```

# 2. **构建并推送 `API` 企业版镜像**：
#    ```bash
#    IMAGE_TAG=latest DOCKER_REPO=myDockerHubID PUSH_IMAGE=1 bash build.sh ee
#    ```

# 3. **构建并签名企业版镜像**：
#    ```bash
#    IMAGE_TAG=latest DOCKER_REPO=myDockerHubID SIGN_IMAGE=1 SIGN_KEY=path/to/key bash build.sh ee
#    ```

# ### 总结

# 该脚本实现了 API 模块的 Docker 镜像的自动化构建、推送和签名功能，支持企业版和开源版的构建。通过传入不同的环境变量，可以灵活控制构建的流程。同时还提供了 Helm 图表更新的功能，确保版本的一致性。