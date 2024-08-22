### Prerequisites

- [Vagrant](../scripts/vagrant/README.md)
- Python 3.9
- Pipenv

### Development environment

```bash
cd openreplay/api
# Make your own copy of .env file and edit it as you want
cp .env.dev .env

# Create a .venv folder to contain all you dependencies
mkdir .venv

# Installing dependencies (pipenv will detect the .venv folder and use it as a target)
pipenv install -r requirements.txt [--skip-lock]
```

### Building and deploying locally

```bash
cd openreplay-contributions
vagrant ssh
cd openreplay-dev/openreplay/scripts/helmcharts
# For complete list of options
# bash local_deploy.sh help
bash local_deploy.sh api
```

<!-- 
### 前提条件

1. **Vagrant**：请参考[Vagrant设置指南](../scripts/vagrant/README.md)来安装和配置Vagrant。
2. **Python 3.9**：确保您已经安装了Python 3.9。您可以从官方[Python网站](https://www.python.org/downloads/release/python-390/)下载。
3. **Pipenv**：安装Pipenv来管理Python依赖包和虚拟环境，使用以下命令：

   ```bash
   pip install pipenv
   ```

### 开发环境设置

1. 进入API目录：

   ```bash
   cd openreplay/api
   ```

2. 复制`.env`配置文件并根据需要进行修改：

   ```bash
   cp .env.dev .env
   ```

3. 创建一个`.venv`文件夹，用于存放虚拟环境中的所有依赖项：

   ```bash
   mkdir .venv
   ```

4. 使用Pipenv安装所需的依赖项，Pipenv会自动检测`.venv`文件夹并将其作为安装目标：

   ```bash
   pipenv install -r requirements.txt [--skip-lock]
   ```

   可选的`--skip-lock`标志允许您跳过生成锁定文件的步骤，特别是在开发过程中可以加快安装速度。

### 本地构建与部署

1. 进入`openreplay-contributions`目录：

   ```bash
   cd openreplay-contributions
   ```

2. 启动Vagrant环境：

   ```bash
   vagrant ssh
   ```

3. 进入Vagrant环境后，导航到Helm charts目录：

   ```bash
   cd openreplay-dev/openreplay/scripts/helmcharts
   ```

4. 查看所有可用的部署选项，使用以下命令：

   ```bash
   bash local_deploy.sh help
   ```

5. 要在本地部署API，运行：

   ```bash
   bash local_deploy.sh api
   ```

这样可以在本地开发环境中构建、运行和测试OpenReplay API。通过使用Vagrant、Helm和Pipenv，您可以确保您的开发环境保持一致和隔离，使开发过程更加高效和易于管理。 -->