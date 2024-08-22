#!/bin/bash

# Script to build alerts module
# flags to accept:
# envarg: build for enterprise edition.
# Default will be OSS build.

# Usage: IMAGE_TAG=latest DOCKER_REPO=myDockerHubID bash build.sh <ee>

git_sha=$(git rev-parse --short HEAD)
image_tag=${IMAGE_TAG:-git_sha}
envarg="default-foss"
source ../scripts/lib/_docker.sh
check_prereq() {
    which docker || {
        echo "Docker not installed, please install docker."
        exit 1
    }
}

[[ $1 == ee ]] && ee=true
[[ $PATCH -eq 1 ]] && {
    image_tag="$(grep -ER ^.ppVersion ../scripts/helmcharts/openreplay/charts/$chart | xargs | awk '{print $2}' | awk -F. -v OFS=. '{$NF += 1 ; print}')"
    [[ $ee == "true" ]] && {
        image_tag="${image_tag}-ee"
    }
}
update_helm_release() {
    chart=$1
    HELM_TAG="$(grep -iER ^version ../scripts/helmcharts/openreplay/charts/$chart | awk '{print $2}' | awk -F. -v OFS=. '{$NF += 1 ; print}')"
    # Update the chart version
    sed -i "s#^version.*#version: $HELM_TAG# g" ../scripts/helmcharts/openreplay/charts/$chart/Chart.yaml
    # Update image tags
    sed -i "s#ppVersion.*#ppVersion: \"$image_tag\"#g" ../scripts/helmcharts/openreplay/charts/$chart/Chart.yaml
    # Commit the changes
    git add ../scripts/helmcharts/openreplay/charts/$chart/Chart.yaml
    git commit -m "chore(helm): Updating $chart image release"
}

function build_alerts() {
    destination="_alerts"
    [[ $1 == "ee" ]] && {
        destination="_alerts_ee"
    }
    cp -R ../api ../${destination}
    cd ../${destination}
    tag=""
    # Copy enterprise code
    [[ $1 == "ee" ]] && {
        cp -rf ../ee/api/* ./
        envarg="default-ee"
        tag="ee-"
    }
    mv Dockerfile_alerts.dockerignore .dockerignore
    docker build -f ./Dockerfile_alerts --platform linux/${ARCH:-"amd64"} --build-arg envarg=$envarg --build-arg GIT_SHA=$git_sha -t ${DOCKER_REPO:-'local'}/alerts:${image_tag} .
    cd ../api
    rm -rf ../${destination}
    [[ $PUSH_IMAGE -eq 1 ]] && {
        docker push ${DOCKER_REPO:-'local'}/alerts:${image_tag}
        docker tag ${DOCKER_REPO:-'local'}/alerts:${image_tag} ${DOCKER_REPO:-'local'}/alerts:${tag}latest
        docker push ${DOCKER_REPO:-'local'}/alerts:${tag}latest
    }
    [[ $SIGN_IMAGE -eq 1 ]] && {
        cosign sign --key $SIGN_KEY ${DOCKER_REPO:-'local'}/alerts:${image_tag}
    }
    echo "completed alerts build"
}

check_prereq
build_alerts $1
if [[ $PATCH -eq 1 ]]; then
    update_helm_release alerts
fi


# ### 这个 Bash 脚本的作用

# 该脚本用于构建 `alerts` 模块的 Docker 镜像，并根据传入的参数选择是否构建企业版(enterprise edition, `ee`)。默认情况下，它将构建开源版本 (OSS)。此外，脚本还会根据需要更新 Helm chart 并处理镜像的推送和签名。

# ### 脚本详解

# 1. **环境变量**:
#    - `IMAGE_TAG`：如果未提供，则使用当前 Git 提交的短哈希作为镜像标签。
#    - `DOCKER_REPO`：指定 Docker 镜像的目标仓库，默认值是 `local`。
#    - `envarg`：用于区分构建的类型，`default-foss` 表示开源版，`default-ee` 表示企业版。

# 2. **主要功能**:
#    - 检查 Docker 是否安装。
#    - 根据参数决定构建开源版还是企业版。
#    - 构建 Docker 镜像。
#    - 如果设置了 `PATCH=1`，还会自动更新 Helm chart 的版本和镜像标签。
#    - 可选地推送镜像到 Docker registry。
#    - 可选地使用 `cosign` 工具对镜像进行签名。

# ### 关键步骤与解释

# 1. **检查 Docker 是否安装 (`check_prereq`)**:
#    该函数通过 `which docker` 检查 Docker 是否已安装，如果未安装则退出并打印提示信息。

# 2. **参数处理**:
#    - 如果脚本运行时传入的第一个参数是 `ee`，则将变量 `ee` 设置为 `true`，表示构建企业版镜像。
#    - 如果环境变量 `PATCH` 的值为 `1`，则会更新 Helm chart 的 `ppVersion` 字段并递增图表的版本号。

# 3. **构建镜像 (`build_alerts`)**:
#    - 如果构建的是企业版 (`ee`)，会从 `../ee/api/` 目录拷贝企业版相关代码。
#    - 使用 `Dockerfile_alerts` 构建 `alerts` 模块的 Docker 镜像，并根据传入的参数和环境变量生成不同的镜像标签。
#    - 如果 `PUSH_IMAGE` 环境变量为 `1`，则将构建好的镜像推送到 Docker registry。
#    - 如果 `SIGN_IMAGE` 环境变量为 `1`，则使用 `cosign` 对镜像进行签名。

# 4. **更新 Helm chart (`update_helm_release`)**:
#    - 该函数用于递增 Helm chart 版本号并更新其中的 `ppVersion` 字段，以反映新的镜像版本。
#    - 修改完成后，会将更改提交到 Git 仓库。

# ### 参数和环境变量

# - **`IMAGE_TAG`**：用于指定 Docker 镜像标签。如果未指定，则使用当前 Git 提交的短哈希值。
# - **`DOCKER_REPO`**：Docker 镜像推送的目标仓库。如果未指定，默认为 `local`。
# - **`ARCH`**：用于指定镜像的构建架构，默认值为 `amd64`。
# - **`PATCH`**：如果设置为 `1`，脚本会更新 Helm chart 的版本并提交更改。
# - **`PUSH_IMAGE`**：如果设置为 `1`，镜像会被推送到 Docker registry。
# - **`SIGN_IMAGE`**：如果设置为 `1`，使用 `cosign` 对镜像进行签名。
# - **`SIGN_KEY`**：用于签名镜像的密钥路径。

# ### 使用示例

# 1. **构建开源版镜像**:
#    ```bash
#    IMAGE_TAG=latest DOCKER_REPO=myDockerHubID bash build.sh
#    ```

# 2. **构建企业版镜像并推送到 Docker registry**:
#    ```bash
#    IMAGE_TAG=latest DOCKER_REPO=myDockerHubID PUSH_IMAGE=1 bash build.sh ee
#    ```

# 3. **构建并更新 Helm chart**:
#    ```bash
#    IMAGE_TAG=latest DOCKER_REPO=myDockerHubID PATCH=1 bash build.sh
#    ```

# ### 总结

# 这个脚本自动化了构建 `alerts` 模块 Docker 镜像的过程，同时为开源版和企业版提供了灵活的构建选项。通过简单的环境变量控制，脚本能够处理镜像构建、推送、签名以及 Helm chart 的更新，是一个用于持续集成和持续部署的高效工具。