# PPTAgent Docker 部署问题排查手册

**文档版本**: 1.0
**创建日期**: 2026-01-04
**适用版本**: PPTAgent 0.2.16+

---

## 目录

0. [为什么必须使用 Docker](#0-为什么必须使用-docker)
1. [Docker 构建问题](#1-docker-构建问题)
2. [MCP Server 启动失败](#2-mcp-server-启动失败)
3. [配置文件体系](#3-配置文件体系)
4. [架构理解问题](#4-架构理解问题)
5. [常见运维问题](#5-常见运维问题)
6. [快速检查清单](#6-快速检查清单)

---

## 0. 为什么必须使用 Docker

### 0.1 CentOS 7 系统兼容性问题

**宿主机环境**：
```bash
$ cat /etc/os-release
NAME="CentOS Linux"
VERSION="7 (Core)"
ID="centos"
VERSION_ID="7"
```

**核心问题**：CentOS 7 的 **GLIBC 版本过旧**，无法运行 Playwright 和 Chromium。

---

### 0.2 GLIBC 版本要求

| 组件 | 最低 GLIBC 要求 | CentOS 7 GLIBC 版本 | 兼容性 |
|------|----------------|-------------------|--------|
| **Playwright** | GLIBC 2.27+ | GLIBC 2.17 | ❌ 不兼容 |
| **Chromium** | GLIBC 2.27+ | GLIBC 2.17 | ❌ 不兼容 |
| **Python 3.11** | GLIBC 2.17+ | GLIBC 2.17 | ✅ 兼容 |

**验证 GLIBC 版本**：
```bash
# CentOS 7 宿主机
$ ldd --version
ldd (GNU libc) 2.17
Copyright (C) 2012 Free Software Foundation, Inc.
```

---

### 0.3 虚拟环境安装失败示例

**尝试在 CentOS 7 虚拟环境中安装**：

```bash
# 创建虚拟环境
conda create -n pptagent python=3.11
conda activate pptagent

# 安装依赖
pip install playwright
playwright install chromium

# ❌ 运行时报错
playwright install-deps
```

**错误信息**：
```
Error: /lib64/libc.so.6: version `GLIBC_2.27' not found
Error: /lib64/libc.so.6: version `GLIBC_2.28' not found
```

**原因分析**：
- Playwright 编译时链接了 GLIBC 2.27+
- Chromium 二进制依赖 GLIBC 2.27+ 的符号
- CentOS 7 只提供 GLIBC 2.17（2012年发布）
- 无法升级 GLIBC（会导致系统崩溃）

---

### 0.4 Docker 如何解决问题

**Docker 容器使用 Debian 12（Bookworm）**：

```dockerfile
FROM python:3.11-slim
# 基于 Debian 12，GLIBC 2.36
```

**版本对比**：

| 系统 | GLIBC 版本 | 发布时间 | Playwright 支持 |
|------|-----------|---------|---------------|
| CentOS 7 | 2.17 | 2012 | ❌ 不支持 |
| CentOS 8 | 2.28 | 2019 | ✅ 支持 |
| Ubuntu 20.04 | 2.31 | 2020 | ✅ 支持 |
| Debian 11 | 2.31 | 2021 | ✅ 支持 |
| **Debian 12** | **2.36** | **2023** | ✅ 完美支持 |

**Docker 优势**：
- ✅ 容器内使用 Debian 12（GLIBC 2.36）
- ✅ 与宿主机 CentOS 7 完全隔离
- ✅ Playwright 和 Chromium 正常运行
- ✅ 无需升级宿主机系统

---

### 0.5 其他尝试的方案（失败）

#### 方案 1：手动编译 GLIBC（❌ 不可行）

```bash
# ⚠️ 危险操作，会导致系统崩溃！
wget https://ftp.gnu.org/gnu/glibc/glibc-2.36.tar.gz
tar -xzf glibc-2.36.tar.gz
cd glibc-2.36
./configure --prefix=/usr
make && make install
```

**失败原因**：
- 系统核心程序（bash, ls, systemd）依赖 GLIBC 2.17
- 升级后会导致系统无法启动
- 回滚极其困难

---

#### 方案 2：使用 Conda 提供的 GLIBC（❌ 部分成功）

```bash
conda install -c conda-forge glibc_linux-64=2.28
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
```

**失败原因**：
- Conda GLIBC 与系统 GLIBC 冲突
- 部分依赖仍然链接到系统 GLIBC
- Playwright 安装 Chromium 时失败

---

#### 方案 3：使用静态编译的 Chromium（❌ 复杂度高）

```bash
# 使用 Chrome for Testing
wget https://storage.googleapis.com/chrome-for-testing-public/...
```

**失败原因**：
- Playwright 仍需 GLIBC 2.27+
- 即使 Chromium 可用，Playwright 本身仍会报错
- 配置复杂，维护困难

---

### 0.6 Docker 是唯一可行方案

**结论**：在 CentOS 7 环境下，**Docker 是运行 PPTAgent 的唯一可行方案**。

**对比表**：

| 方案 | 可行性 | 复杂度 | 稳定性 | 推荐度 |
|------|-------|--------|--------|--------|
| **Docker 容器** | ✅ 完全可行 | 低 | 高 | ⭐⭐⭐⭐⭐ |
| 升级宿主机到 CentOS 8+ | ✅ 可行 | 高（需停机） | 高 | ⭐⭐⭐ |
| 虚拟环境 | ❌ 不可行 | - | - | ❌ |
| 手动编译 GLIBC | ❌ 危险 | 极高 | 极低 | ❌ |
| Conda GLIBC | ❌ 不稳定 | 高 | 低 | ❌ |

**Docker 优势总结**：
1. ✅ **零风险**：不影响宿主机系统
2. ✅ **简单**：一次构建，到处运行
3. ✅ **隔离**：依赖冲突完全隔离
4. ✅ **可维护**：版本管理清晰
5. ✅ **可扩展**：支持 GPU、集群部署

---

### 0.7 其他老旧系统的类似问题

**同样需要 Docker 的系统**：

| 系统 | GLIBC 版本 | Playwright 兼容性 | 推荐方案 |
|------|-----------|-----------------|---------|
| CentOS 7 | 2.17 | ❌ | Docker |
| RHEL 7 | 2.17 | ❌ | Docker |
| Ubuntu 16.04 | 2.23 | ❌ | Docker 或升级系统 |
| Debian 9 | 2.24 | ❌ | Docker 或升级系统 |
| Ubuntu 18.04 | 2.27 | ⚠️ 勉强可用 | Docker（推荐） |

**建议**：
- CentOS 7/RHEL 7：**必须使用 Docker**
- Ubuntu 16.04/18.04：**强烈推荐 Docker**
- Ubuntu 20.04+：可以虚拟环境或 Docker
- Debian 11+：可以虚拟环境或 Docker

---

## 1. Docker 构建问题

### 1.1 Git Clone 超时错误

**错误信息**：
```
Cloning into '/app/PPTAgent'...
error: RPC failed; curl 28 GnuTLS recv error (-110): The TLS connection was non-properly terminated.
fatal: expected flush after ref listing
```

**原因分析**：
- 网络不稳定导致 git clone 超时
- GitHub 大仓库拉取失败（PPTAgent 约 200MB+）
- 构建时从远程克隆代码容易受网络影响

**解决方案**：

**方案 A：使用本地代码（推荐）**

修改 `Dockerfile`：
```dockerfile
# 原来（容易超时）
ARG CACHE_DATE=UNKNOWN
RUN git clone https://github.com/icip-cas/PPTAgent /app/PPTAgent

# 改为（稳定可靠）
COPY . /app/PPTAgent
```

**方案 B：使用国内镜像**（如果必须 git clone）
```dockerfile
RUN git clone https://gitee.com/mirrors/PPTAgent /app/PPTAgent
# 或使用 ghproxy
RUN git clone https://ghproxy.com/https://github.com/icip-cas/PPTAgent /app/PPTAgent
```

**预防措施**：
- ✅ 优先使用本地代码 COPY
- ✅ 挂载本地代码目录到容器（`-v $(pwd):/app/PPTAgent`）
- ✅ 网络代理配置：`docker build --build-arg HTTP_PROXY=...`

---

### 1.2 CACHE_DATE 构建参数警告

**警告信息**：
```
[Warning] One or more build-args [CACHE_DATE] were not consumed
```

**原因分析**：
- Makefile 中传递了 `--build-arg CACHE_DATE=...`
- 但 Dockerfile 中删除了 `ARG CACHE_DATE`（改用 COPY 后不再需要）
- Docker 发现参数未被使用

**解决方案**：

修改 `Makefile`：
```makefile
# 删除 CACHE_DATE 参数
docker-build:
	docker build \
		--network=host \
		-t pptagent-complete:latest \
		-f Dockerfile \
		.
```

**原理说明**：
- `CACHE_DATE` 原本用于强制重新执行 `git clone`（破坏缓存）
- 使用 `COPY` 后，文件变化会自动触发重新构建
- 不再需要 `CACHE_DATE` 参数

---

### 1.3 DNS 解析失败

**错误信息**：
```
Temporary failure resolving 'deb.debian.org'
Temporary failure resolving 'download.docker.com'
```

**原因分析**：
- Docker 构建时默认使用容器网络
- 容器 DNS 配置可能与宿主机不一致
- 某些环境下容器无法解析外部域名

**解决方案**：

**方案 A：使用宿主机网络（推荐）**

修改 `Makefile`：
```makefile
docker-build:
	docker build \
		--network=host \  # ← 使用宿主机网络
		-t pptagent-complete:latest \
		-f Dockerfile \
		.
```

**方案 B：指定 DNS 服务器**（备选）
```makefile
docker-build:
	docker build \
		--dns 8.8.8.8 \
		--dns 114.114.114.114 \
		-t pptagent-complete:latest \
		.
```

**优势对比**：
| 方案 | 优点 | 缺点 |
|------|------|------|
| `--network=host` | 简单，与宿主机网络一致 | 构建时占用宿主机端口 |
| `--dns` | 明确指定 DNS | 需要手动配置多个 DNS |

---

### 1.4 Docker GPG 密钥下载失败

**错误信息**：
```
curl: (35) Recv failure: Connection reset by peer
gpg: no valid OpenPGP data found.
The command '... && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor ...' returned a non-zero code: 2
```

**原因分析**：
- 下载 Docker 官方 GPG 密钥时网络连接被重置
- download.docker.com 连接不稳定
- 即使使用 `--network=host` 也可能失败（取决于网络环境）

**解决方案（已采用）**：

**挂载宿主机 Docker CLI（推荐）**

不在容器内安装 Docker CLI，而是从宿主机挂载二进制文件：

**修改 `Dockerfile`（第 17-36 行）**：
```dockerfile
# 删除 Docker CLI 安装部分
# 原来：
# && apt-get install -y gnupg lsb-release \
# && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor ... \
# && apt-get install -y docker-ce-cli=5:20.10.* \

# 修改后（只安装基础依赖）：
# NOTE: Docker CLI will be mounted from host at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make git libreoffice poppler-utils curl wget ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
```

**修改 `Makefile`（第 141、166 行）**：
```makefile
# 添加 Docker CLI 挂载
docker run -dt \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /usr/bin/docker:/usr/bin/docker:ro \  # ← 挂载宿主机 Docker CLI（只读）
    -v $(pwd):/app/PPTAgent \
    ...
```

**优势**：
- ✅ **完全避免网络下载问题**（无需下载 GPG 密钥、Docker 仓库）
- ✅ **版本完全匹配**（容器内 Docker CLI 与宿主机 Docker daemon 版本一致）
- ✅ **减少构建时间**（不需要添加 Docker 仓库和安装 docker-ce-cli）
- ✅ **减少镜像体积**（不安装额外的包）
- ✅ **简化 Dockerfile**（删除复杂的 GPG 密钥处理逻辑）

**验证方法**：
```bash
# 构建镜像（无网络问题）
make docker-build

# 启动容器
make docker-run-cpu

# 验证 Docker CLI 可用
docker exec pptagent docker --version
# 输出：Docker version 20.10.x, build xxxxx（与宿主机一致）

# 验证可以与宿主机 Docker daemon 通信
docker exec pptagent docker ps
# 应该能看到容器列表
```

**其他备选方案**（不推荐）：

**方案 B：直接下载 Docker 二进制**
```dockerfile
RUN wget https://download.docker.com/linux/static/stable/x86_64/docker-20.10.24.tgz \
    && tar xzvf docker-20.10.24.tgz \
    && cp docker/docker /usr/local/bin/ \
    && rm -rf docker docker-20.10.24.tgz
```
- 劣势：仍需网络下载，可能失败

**方案 C：使用国内镜像**
```dockerfile
RUN curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/debian/gpg | gpg --dearmor ...
```
- 劣势：镜像源也可能不稳定

---

## 2. MCP Server 启动失败

### 2.1 deeppresenter Server 路径错误

**错误信息**：
```
error: Failed to spawn: `deeppresenter/tools/server.py`
  Caused by: No such file or directory (os error 2)
ERROR: Error connecting to server deeppresenter: Connection closed
```

**原因分析**：
- `mcp.json` 中路径配置错误：`deeppresenter/tools/server.py`
- **项目有两层 deeppresenter 目录**：
  ```
  PPTAgent/
  ├── deeppresenter/          # 第一层：包目录
  │   ├── deeppresenter/      # 第二层：Python 包
  │   │   └── tools/          # ← 这里才是 tools 目录
  │   │       └── server.py
  ```
- 路径缺少第二层 `deeppresenter/`

**解决方案**：

修改 `deeppresenter/deeppresenter/mcp.json`：
```json
{
    "name": "deeppresenter",
    "command": "uv",
    "args": [
        "run",
        "deeppresenter/deeppresenter/tools/server.py",  // ← 两层 deeppresenter
        "$WORKSPACE"
    ]
}
```

**验证方法**：
```bash
# 在容器内验证路径
docker exec pptagent ls -la /app/PPTAgent/deeppresenter/deeppresenter/tools/server.py

# 查看日志确认启动成功
make docker-logs | grep "deeppresenter"
# 期望输出：INFO - Connected to server deeppresenter.
```

---

### 2.2 Docker API 版本不兼容

**错误信息**：
```
docker: Error response from daemon: client version 1.52 is too new. Maximum supported API version is 1.41
ERROR: Error connecting to server desktop_commander: Connection closed
```

**原因分析**：
- 容器内安装的 Docker CLI 版本太新（27.x，API 1.52）
- 宿主机 Docker daemon 版本较旧（< 25.x，最高支持 API 1.41）
- API 版本不兼容导致无法通信

**版本对应关系**：
| Docker CLI | API 版本 | Docker daemon 要求 |
|-----------|---------|-------------------|
| 27.x | 1.52 | >= 27.x |
| 25.x | 1.44 | >= 25.x |
| 20.10.x | 1.41 | >= 20.10.x ✅ 兼容 |

**解决方案**：

**方案 A：挂载宿主机 Docker CLI（推荐，已采用）**

修改 `Dockerfile` 和 `Makefile`：

```dockerfile
# Dockerfile：不再安装 Docker CLI
# NOTE: Docker CLI will be mounted from host at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make git libreoffice poppler-utils curl wget ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
```

```makefile
# Makefile：挂载宿主机 Docker CLI
docker run -dt \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /usr/bin/docker:/usr/bin/docker:ro \
    ...
```

**优势**：
- ✅ 完全避免 Docker GPG 密钥下载失败（网络问题）
- ✅ 版本完全匹配（使用宿主机相同版本）
- ✅ 减少镜像构建时间
- ✅ 减少镜像体积

**方案 B：降级容器内 Docker CLI**（备选，已废弃）

```dockerfile
# 容易遇到网络下载问题
&& apt-get install -y --no-install-recommends docker-ce-cli=5:20.10.* \
```

**方案 C：升级宿主机 Docker**（如果有权限）

```bash
# 查看宿主机版本
docker version

# 升级 Docker（需要 root 权限）
curl -fsSL https://get.docker.com | sh
```

**验证兼容性**：
```bash
# 在容器内检查 Docker CLI 版本
docker exec pptagent docker --version
# 输出：Docker version 20.10.x

# 测试是否能与宿主机通信
docker exec pptagent docker ps
# 应该能看到容器列表
```

---

### 2.3 PPTAgent.yaml 配置错误

**错误信息**：
```
KeyError: 'agent'
AttributeError: 'DeepPresenterConfig' object has no attribute 'agent'
```

**原因分析**：
- `PPTAgent.yaml` 中配置 `use_model: agent`
- `config.yaml` 中只有以下配置：
  ```yaml
  research_agent: {...}
  design_agent: {...}
  long_context_model: {...}
  vision_model: {...}
  t2i_model: {...}
  # ❌ 没有 agent
  ```
- 代码执行 `config["agent"]` 时找不到对应属性

**对应关系机制**：
```python
# deeppresenter/agents/agent.py
self.llm: LLM = config[role_config.use_model]
# 等价于：config["agent"] → getattr(config, "agent") → 报错！
```

**解决方案**：

修改 `deeppresenter/deeppresenter/roles/PPTAgent.yaml`：
```yaml
# 原来（错误）
use_model: agent

# 改为（正确）
use_model: design_agent  # 或 long_context_model
```

**为什么选择 design_agent？**
- PPTAgent Agent 负责编排任务，选择工具
- design_agent 配置的模型能力适合这个任务
- 与 Design Agent 共享同一模型配置

---

### 2.4 缺少 python-pptx 模块

**错误信息**：
```
ModuleNotFoundError: No module named 'pptx'
  File "/app/PPTAgent/deeppresenter/deeppresenter/tools/task.py", line 8, in <module>
    from pptx import Presentation
ERROR: Error connecting to server deeppresenter: Connection closed
```

**原因分析**：
- `deeppresenter/tools/task.py` 需要导入 `pptx` 模块
- 依赖链：`deeppresenter` → `pptagent>=0.2.16` → `pptagent-pptx>=0.0.1`
- Dockerfile 只安装了 `deeppresenter`，没有显式安装 `pptagent`
- 可编辑模式（`-e`）安装时，级联依赖可能不完整

**解决方案**：

修改 `Dockerfile`（第 46-48 行）：
```dockerfile
# 原来（依赖安装不完整）
RUN uv pip install --system -e ./deeppresenter && \
    uv pip install --system playwright

# 改为（显式安装 pptagent）
RUN uv pip install --system -e ./pptagent && \
    uv pip install --system -e ./deeppresenter && \
    uv pip install --system playwright
```

**为什么要显式安装 pptagent？**
- `pptagent` 提供核心功能和 `pptagent-pptx` 依赖
- 显式安装确保所有依赖正确安装
- 可编辑模式下，先安装 pptagent 再安装 deeppresenter，避免依赖缺失

**验证方法**：
```bash
# 重新构建镜像
make docker-build

# 启动容器
make docker-run-cpu

# 验证 pptx 模块可用
docker exec pptagent python -c "from pptx import Presentation; print('OK')"
# 期望输出：OK

# 查看日志确认 deeppresenter server 启动成功
make docker-logs | grep "Connected to server deeppresenter"
# 期望输出：INFO - Connected to server deeppresenter.
```

---

## 3. 配置文件体系

### 3.1 三个配置文件的关系

PPTAgent 项目有三个关键配置文件，**作用不同，不能互相替代**：

| 配置文件 | 路径 | 用途 | 读取时机 | 能否删除 |
|---------|------|------|---------|---------|
| **.env** | `PPTAgent/.env` | 运行时环境变量 | 容器启动时（`--env-file .env`） | ❌ 不能 |
| **config.yaml** | `deeppresenter/deeppresenter/config.yaml` | Agent 模型配置 | AgentLoop 初始化时 | ⚠️ 使用 deeppresenter 时不能 |
| **mcp.json** | `deeppresenter/deeppresenter/mcp.json` | MCP Server 配置 | AgentEnv 连接 servers 时 | ⚠️ 使用 deeppresenter 时不能 |

---

### 3.2 .env 文件

**作用**：提供运行时环境变量（API keys、服务地址等）

**使用场景**：
- ✅ Docker 容器启动时加载（`docker run --env-file .env`）
- ✅ Makefile 的 `check-env` 验证配置
- ✅ 所有需要 API keys 的地方

**典型配置**：
```bash
# .env
OPENAI_API_KEY=sk-xxxxx
API_BASE=https://api.siliconflow.cn/v1
LANGUAGE_MODEL=Qwen/Qwen2.5-72B-Instruct
VISION_MODEL=Qwen/Qwen2-VL-72B-Instruct
TAVILY_API_KEY=tvly-xxxxx
MINERU_API=http://localhost:8000/file_parse
```

**安全注意事项**：
- ✅ 已添加到 `.gitignore`，不会提交到 git
- ✅ 提供 `.env.example` 作为模板
- ❌ 不要在 Dockerfile 中写入 API keys（会永久存储到镜像）

---

### 3.3 config.yaml 文件

**作用**：配置 deeppresenter 各 Agent 使用的 LLM 模型

**配置结构**：
```yaml
# deeppresenter/deeppresenter/config.yaml

research_agent:           # Research Agent 的模型
  base_url: "..."
  model: "..."
  api_key: "..."

design_agent:             # Design Agent 的模型
  base_url: "..."
  model: "..."
  api_key: "..."

long_context_model:       # 长文本处理模型
  base_url: "..."
  model: "..."
  api_key: "..."

vision_model:             # 视觉模型（图像理解）
  base_url: "..."
  model: "..."
  api_key: "..."

t2i_model:                # Text-to-Image 模型（文生图）
  base_url: "..."
  model: "stabilityai/stable-diffusion-3-5-large"
  api_key: "..."
  sampling_parameters:
    response_format: "b64_json"
    extra_body: { "watermark": false }
```

**Agent 如何使用**：
```python
# deeppresenter/agents/agent.py
role_config = RoleConfig(**yaml.safe_load("roles/Research.yaml"))
# Research.yaml: use_model: research_agent

self.llm = config[role_config.use_model]
# 等价于：config["research_agent"]
# 获取 config.yaml 中的 research_agent 配置
```

**推荐配置**（硅基流动）：
```yaml
research_agent:
  base_url: "https://api.siliconflow.cn/v1"
  model: "Qwen/Qwen2.5-72B-Instruct"
  api_key: "sk-your-key"

design_agent:
  base_url: "https://api.siliconflow.cn/v1"
  model: "Qwen/Qwen2.5-72B-Instruct"
  api_key: "sk-your-key"

long_context_model:
  base_url: "https://api.siliconflow.cn/v1"
  model: "deepseek-ai/DeepSeek-V3"  # 64K 上下文
  api_key: "sk-your-key"

vision_model:
  base_url: "https://api.siliconflow.cn/v1"
  model: "Qwen/Qwen2-VL-72B-Instruct"
  api_key: "sk-your-key"

t2i_model:
  base_url: "https://api.siliconflow.cn/v1"
  model: "stabilityai/stable-diffusion-3-5-large"
  api_key: "sk-your-key"
  sampling_parameters:
    response_format: "b64_json"
    extra_body: { "watermark": false }
```

---

### 3.4 mcp.json 文件

**作用**：配置 3 个 MCP (Model Context Protocol) Servers

**MCP Servers 列表**：
```json
[
    {
        "name": "deeppresenter",
        "description": "DeepPresenter Tools",
        "command": "uv",
        "args": ["run", "deeppresenter/deeppresenter/tools/server.py", "$WORKSPACE"],
        "env": {
            "TAVILY_API_KEY": "tvly-xxxxx",
            "MINERU_API_KEY": "your_key",
            "MIN_IMAGE_SIZE": "921600"
        }
    },
    {
        "name": "pptagent",
        "description": "PPTAgent MCP Server",
        "command": "uv",
        "args": ["run", "pptagent-mcp"],
        "env": {
            "PPTAGENT_MODEL": "Qwen/Qwen2.5-72B-Instruct",
            "PPTAGENT_API_KEY": "sk-xxxxx",
            "PPTAGENT_API_BASE": "https://api.siliconflow.cn/v1"
        }
    },
    {
        "name": "desktop_commander",
        "description": "Docker Sandbox",
        "command": "docker",
        "args": [
            "run", "--security-opt", "seccomp=unconfined",
            "--init", "--name", "$WORKSPACE_ID", "-i", "--rm",
            "-v", "$WORKSPACE:$WORKSPACE", "-w", "$WORKSPACE",
            "desktop-commander-deeppresenter"
        ]
    }
]
```

**3 个 MCP Servers 的职责**：

| Server | 用途 | 提供的工具 | 何时使用 |
|--------|------|----------|---------|
| **deeppresenter** | 搜索、文档解析等工具 | `tavily_search`, `fetch_url`, `markdown_to_pptx` 等 | Research Agent 工作时 |
| **pptagent** | 生成 PPT | `set_template`, `create_slide`, `generate_slide` 等 | PPTAgent Agent 调用工具时 |
| **desktop_commander** | Docker 沙盒执行命令 | `execute_command`, `read_file`, `write_file` 等 | Design Agent 执行代码时 |

**启动时机**：
```python
# deeppresenter/agents/env.py
async with AgentEnv(workspace, hci_enable) as agent_env:
    # ← 这里自动连接所有 MCP servers
    await self.mcp_client.connect_servers(config.mcp_config_file)
```

---

### 3.5 配置文件修改后是否需要重新构建？

| 修改的文件 | 是否需要重新构建 | 操作 |
|-----------|----------------|------|
| `.env` | ❌ 否 | `make docker-restart` |
| `config.yaml` | ❌ 否 | `make docker-restart` |
| `mcp.json` | ❌ 否 | `make docker-restart` |
| `*.py` 代码文件 | ❌ 否（已挂载） | `make docker-restart` |
| `pyproject.toml` | ✅ 是 | `make docker-build` |
| `Dockerfile` | ✅ 是 | `make docker-build` |

**原因**：
- 配置文件和代码通过 `-v $(pwd):/app/PPTAgent` 挂载
- 修改本地文件，容器内立即生效
- 只有依赖或系统包变化才需要重新构建

---

## 4. 架构理解问题

### 4.1 两层模型架构

PPTAgent 在"模版"模式下使用**两层模型架构**：

```
用户请求 → AgentLoop
  ↓
【第一层：编排层】
PPTAgent Agent
  - 配置来源：PPTAgent.yaml: use_model → config.yaml
  - 使用模型：design_agent (Qwen3-30B)
  - 职责：理解任务、决定调用哪些工具、按什么顺序

  ↓ 调用 MCP 工具

【第二层：执行层】
pptagent MCP Server
  - 配置来源：mcp.json: PPTAGENT_MODEL
  - 使用模型：Qwen3-30B (可以与第一层不同)
  - 职责：实际生成幻灯片（选布局、写内容、生成代码）
```

---

### 4.2 两层模型的调用流程

**完整示例**：

```
用户："根据这个 Markdown 生成10页PPT"
  ↓
【编排层】PPTAgent Agent (config.yaml: design_agent)
  推理："需要生成10页PPT，先选择模板，然后循环生成每一页"

  调用序列：
  1. list_templates()          → pptagent MCP Server
  2. set_template("default")   → pptagent MCP Server
  3. 循环10次：
     a. create_slide("layout_1")       → pptagent MCP Server
     b. write_slide([{...}])           → pptagent MCP Server
     c. generate_slide()               → pptagent MCP Server
        ↓
        【执行层】pptagent MCP Server (mcp.json: PPTAGENT_MODEL)
        内部运行3个 agents：
        - layout_selector: 选择最合适的布局
        - editor: 根据模板限制生成内容
        - coder: 将内容转换为幻灯片编辑代码

        返回：生成的幻灯片
  4. save_generated_slides("output.pptx")
```

**关键点**：
- 第一层（编排）：决策"做什么"（what to do）
- 第二层（执行）：实现"怎么做"（how to do）
- 两层可以使用相同或不同的模型

---

### 4.3 PPTAGENT_MODEL 何时使用？

**使用时机**：

1. **启动时读取**（pptagent MCP Server 初始化）：
```python
# pptagent/mcp_server.py
class PPTAgentServer(PPTAgent):
    def __init__(self):
        model = AsyncLLM(
            os.getenv("PPTAGENT_MODEL"),        # ← 读取环境变量
            os.getenv("PPTAGENT_API_BASE"),
            os.getenv("PPTAGENT_API_KEY"),
        )
        super().__init__(language_model=model, vision_model=model)
```

2. **调用时使用**（generate_slide 工具被调用）：
```python
async def generate_slide():
    # 使用 PPTAGENT_MODEL 运行以下 agents：
    command_list = self._generate_commands(...)  # layout_selector, editor
    slide = await self._edit_slide(...)          # coder
```

**验证方法**：
```bash
make docker-logs | grep "pptagent"

# 期望输出：
# INFO - 6 templates loaded successfully: thu, beamer, hit, default, cip, ucas
# INFO - Starting MCP server 'PPTAgent' with transport 'stdio'
```

---

### 4.4 t2i_model 是什么？

**t2i = Text-to-Image（文生图模型）**

**用途**：
- 根据文本描述自动生成图片
- 在 Research Agent 搜索不到合适图片时使用
- 为演示文稿生成配图

**推荐模型**（硅基流动）：
```yaml
t2i_model:
  base_url: "https://api.siliconflow.cn/v1"
  model: "stabilityai/stable-diffusion-3-5-large"  # 推荐
  api_key: "sk-xxxxx"
  sampling_parameters:
    response_format: "b64_json"
    extra_body: { "watermark": false }
```

**其他可选模型**：
- `black-forest-labs/FLUX.1-schnell` - 速度快
- `Kwai-Kolors/Kolors` - 中文理解好

**是否必需**：
- ❌ 不是必需的
- 如果不需要自动生成图片，可以配置占位符
- 只在明确调用生成图片功能时使用

---

## 5. 常见运维问题

### 5.1 何时需要重新构建镜像？

| 修改类型 | 示例 | 是否需要重新构建 | 操作 |
|---------|------|----------------|------|
| **系统依赖** | Dockerfile 中的 `apt-get install` | ✅ 是 | `make docker-build` |
| **Python 包依赖** | `pyproject.toml` 中的 `dependencies` | ✅ 是 | `make docker-build` |
| **基础镜像** | `FROM python:3.11` 改为 `FROM python:3.12` | ✅ 是 | `make docker-build` |
| **环境变量定义** | Dockerfile 中的 `ENV` 指令 | ✅ 是 | `make docker-build` |
| **镜像层操作** | 添加/删除 `RUN` 命令 | ✅ 是 | `make docker-build` |
| **Python 代码** | `*.py` 文件修改 | ❌ 否 | `make docker-restart` |
| **配置文件** | `.env`, `config.yaml`, `mcp.json` | ❌ 否 | `make docker-restart` |
| **模板文件** | `roles/*.yaml`, `templates/*` | ❌ 否 | `make docker-restart` |

**判断标准**：
- ✅ **需要重新构建**：修改了镜像内部的东西（系统包、Python 包、镜像层）
- ❌ **只需重启容器**：修改了挂载的东西（代码、配置文件）

---

### 5.2 代码挂载配置

**Makefile 中的挂载配置**：
```makefile
docker-run-cpu:
	docker run -dt \
		--name pptagent \
		--env-file .env \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v $(pwd):/app/PPTAgent \                      # ← 代码挂载
		-v $$HOME/.cache/huggingface:/root/.cache/huggingface \
		-v $(pwd)/outputs:/app/PPTAgent/outputs \
		--network=host \
		pptagent-complete:latest
```

**挂载优势**：
- ✅ 修改本地代码，容器内立即生效
- ✅ 无需重新构建镜像
- ✅ 开发调试更方便

**注意事项**：
- 必须在项目根目录执行 `make` 命令（`$(pwd)` 才正确）
- 如果修改了依赖（`pyproject.toml`），仍需重新构建

---

### 5.3 路径配置最佳实践

**相对路径 vs 绝对路径**：

| 场景 | 推荐方式 | 示例 |
|------|---------|------|
| **mcp.json 中的路径** | 相对路径 | `deeppresenter/deeppresenter/tools/server.py` |
| **Docker 挂载** | `$(pwd)` 动态路径 | `-v $(pwd):/app/PPTAgent` |
| **容器内路径** | 绝对路径 | `/app/PPTAgent/...` |

**相对路径可以工作的前提**：
```dockerfile
# Dockerfile 设置工作目录
WORKDIR /app/PPTAgent

# webui.py 继承这个工作目录
CMD ["python", "webui.py", "0.0.0.0"]
```

**路径解析过程**：
```
容器工作目录：/app/PPTAgent
  ↓
MCP client 启动 server 时继承工作目录
  ↓
相对路径：deeppresenter/deeppresenter/tools/server.py
  ↓
解析为：/app/PPTAgent/deeppresenter/deeppresenter/tools/server.py ✅
```

---

### 5.4 Makefile 常用命令

```bash
# 环境配置
make setup-env          # 创建 .env 文件（从 .env.example 复制）
make check-env          # 检查环境变量是否设置

# Docker 镜像构建
make docker-build       # 构建主容器镜像
make docker-rebuild     # 强制重新构建（不使用缓存）
make build-sandbox      # 构建沙盒容器（desktop-commander）

# Docker 容器管理
make docker-run         # 启动容器（GPU 模式）
make docker-run-cpu     # 启动容器（CPU 模式）
make docker-stop        # 停止容器
make docker-restart     # 重启容器
make docker-clean       # 删除容器
make docker-logs        # 查看容器日志（实时）
make docker-shell       # 进入容器 shell

# 清理
make clean              # 清理临时文件（__pycache__ 等）
make clean-all          # 清理所有 Docker 资源

# 信息查询
make version            # 显示版本信息
make help               # 显示所有可用命令
```

**典型工作流**：
```bash
# 1. 首次部署
make setup-env          # 创建 .env
vim .env                # 编辑配置
make docker-build       # 构建镜像（10-15分钟）
make build-sandbox      # 构建沙盒镜像（5分钟）
make docker-run-cpu     # 启动服务

# 2. 修改代码后
vim pptagent/pptgen.py
make docker-restart     # 重启容器（3秒）

# 3. 修改依赖后
vim pyproject.toml
make docker-build       # 重新构建（10-15分钟）
make docker-run-cpu

# 4. 查看日志调试
make docker-logs        # Ctrl+C 退出
```

---

## 6. 快速检查清单

### 6.1 部署前检查

- [ ] **系统要求**
  - [ ] Docker 版本 >= 20.10
  - [ ] Git 已安装
  - [ ] 磁盘空间 >= 10GB
  - [ ] 网络可访问 GitHub/Docker Hub

- [ ] **API Keys**
  - [ ] OpenAI/硅基流动 API Key 已申请
  - [ ] Tavily API Key 已申请（deeppresenter 必需）
  - [ ] MinerU API Key 已申请（可选，14天有效期）

- [ ] **配置文件**
  - [ ] `.env` 文件已创建（`make setup-env`）
  - [ ] `config.yaml` 已填写 API keys
  - [ ] `mcp.json` 已配置（检查路径正确）

---

### 6.2 构建检查

- [ ] **Dockerfile 配置**
  - [ ] 使用 `COPY . /app/PPTAgent`（不要 git clone）
  - [ ] Docker CLI 版本兼容（`docker-ce-cli=5:20.10.*`）
  - [ ] 无 CACHE_DATE 参数警告
  - [ ] 工作目录设置正确（`WORKDIR /app/PPTAgent`）

- [ ] **Makefile 配置**
  - [ ] 使用 `--network=host`
  - [ ] 代码挂载配置（`-v $(pwd):/app/PPTAgent`）
  - [ ] Docker socket 挂载（`-v /var/run/docker.sock:...`）

- [ ] **构建成功标志**
  - [ ] 看到 "Successfully built"
  - [ ] 看到 "Successfully tagged pptagent-complete:latest"
  - [ ] 镜像大小合理（约 3-5GB）

---

### 6.3 运行检查

- [ ] **容器启动**
  - [ ] `make docker-run-cpu` 无错误
  - [ ] `docker ps` 可以看到 pptagent 容器
  - [ ] 端口 7861、9297 正常监听

- [ ] **MCP Servers 启动**
  - [ ] pptagent server 启动成功
    ```bash
    make docker-logs | grep "pptagent"
    # 期望：INFO - 6 templates loaded successfully
    ```
  - [ ] deeppresenter server 启动成功
    ```bash
    make docker-logs | grep "deeppresenter"
    # 期望：INFO - Connected to server deeppresenter
    ```
  - [ ] desktop_commander 启动成功
    ```bash
    make docker-logs | grep "desktop_commander"
    # 期望：INFO - Connected to server desktop_commander
    ```

- [ ] **Web UI 访问**
  - [ ] 浏览器访问 http://localhost:7861
  - [ ] 界面正常显示，无 404 错误
  - [ ] 模板选择下拉框有选项（default, thu, beamer 等）

---

### 6.4 功能测试

- [ ] **模版模式测试**
  1. [ ] 上传 Markdown 或 PDF 文件
  2. [ ] 选择模板（如 default）
  3. [ ] 选择页数（如 5）
  4. [ ] 点击"发送"
  5. [ ] 查看日志确认工作流正常
  6. [ ] 下载生成的 PPTX 文件
  7. [ ] 打开 PPTX 验证内容正确

- [ ] **自由生成模式测试**（可选）
  1. [ ] 切换到"自由生成"模式
  2. [ ] 输入指令（如"生成一个关于AI的演示文稿"）
  3. [ ] 验证 Research Agent 搜索资料
  4. [ ] 验证 Design Agent 生成幻灯片
  5. [ ] 下载并验证 PDF 文件

---

### 6.5 故障排查步骤

**如果 Web UI 无法访问**：
```bash
# 1. 检查容器是否运行
docker ps | grep pptagent

# 2. 检查端口是否被占用
netstat -tuln | grep 7861

# 3. 查看容器日志
make docker-logs

# 4. 进入容器检查
make docker-shell
ps aux | grep python
curl http://localhost:7861
```

**如果 MCP Server 启动失败**：
```bash
# 1. 查看具体错误
make docker-logs | grep "ERROR"

# 2. 验证路径是否正确
docker exec pptagent ls -la /app/PPTAgent/deeppresenter/deeppresenter/tools/

# 3. 验证 Docker CLI 可用
docker exec pptagent docker --version

# 4. 手动测试 MCP server
docker exec pptagent uv run deeppresenter/deeppresenter/tools/server.py /tmp
```

**如果生成 PPT 失败**：
```bash
# 1. 检查 API keys 是否正确
docker exec pptagent env | grep API_KEY

# 2. 测试模型连接
docker exec pptagent python -c "
from pptagent.llms import LLM
llm = LLM('Qwen/Qwen2.5-72B-Instruct', 'https://api.siliconflow.cn/v1', 'sk-xxx')
print(llm('Hello'))
"

# 3. 查看完整错误堆栈
make docker-logs | tail -100
```

---

## 7. 常见错误速查表

| 错误信息 | 原因 | 解决方案 | 章节 |
|---------|------|---------|------|
| `git clone: RPC failed` | 网络超时 | 使用 `COPY` 替代 `git clone` | [1.1](#11-git-clone-超时错误) |
| `[Warning] build-args CACHE_DATE` | 参数未使用 | 删除 Makefile 中的 `--build-arg CACHE_DATE` | [1.2](#12-cache_date-构建参数警告) |
| `Temporary failure resolving` | DNS 解析失败 | 使用 `--network=host` | [1.3](#13-dns-解析失败) |
| `curl: (35) Recv failure: Connection reset` | Docker GPG 密钥下载失败 | 挂载宿主机 Docker CLI | [1.4](#14-docker-gpg-密钥下载失败) |
| `deeppresenter/tools/server.py: No such file` | 路径错误 | 改为 `deeppresenter/deeppresenter/tools/server.py` | [2.1](#21-deeppresenter-server-路径错误) |
| `client version 1.52 is too new` | Docker API 不兼容 | 挂载宿主机 Docker CLI（推荐） | [2.2](#22-docker-api-版本不兼容) |
| `KeyError: 'agent'` | 配置文件错误 | 改为 `use_model: design_agent` | [2.3](#23-pptagentyaml-配置错误) |
| `ModuleNotFoundError: No module named 'pptx'` | 缺少 python-pptx 依赖 | 显式安装 pptagent | [2.4](#24-缺少-python-pptx-模块) |
| `Connection to server failed` | MCP server 未启动 | 检查日志，验证路径和配置 | [2](#2-mcp-server-启动失败) |
| 端口 7861 无法访问 | 容器未启动或端口被占用 | `docker ps` 检查，`netstat` 检查端口 | [6.5](#65-故障排查步骤) |

---

## 8. 联系方式与资源

**官方资源**：
- GitHub 仓库：https://github.com/icip-cas/PPTAgent
- 问题反馈：https://github.com/icip-cas/PPTAgent/issues
- 文档首页：README.md

**相关文档**：
- `Makefile` - 完整命令列表
- `pptagent/DOC.md` - PPTAgent 核心文档
- `deeppresenter/README.md` - DeepPresenter 系统文档
- `CLAUDE.md` - 项目架构说明

**API Keys 申请**：
- 硅基流动：https://siliconflow.cn/
- OpenAI：https://platform.openai.com/
- Tavily Search：https://www.tavily.com/
- MinerU：https://mineru.net/apiManage/docs

---

**文档结束**

如有疑问，请参考对应章节或提交 Issue。
