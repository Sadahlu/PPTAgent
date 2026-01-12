# PPTAgent Docker 快速部署指南

**文档版本**: 1.0
**创建日期**: 2026-01-04
**适用版本**: PPTAgent 0.2.16+

---

## 修复清单

本次部署已修复以下问题：

### 1. Dockerfile 修复

**文件**: `F:/dense/PPTAgent/Dockerfile`

**修复内容**：
- ✅ 第 50 行：将 `git clone` 改为 `COPY . /app/PPTAgent`（避免网络超时）
- ✅ 第 17-36 行：移除 Docker CLI 安装（改为挂载宿主机 Docker 二进制）

```dockerfile
# 修复前
ARG CACHE_DATE=UNKNOWN
RUN git clone https://github.com/icip-cas/PPTAgent /app/PPTAgent
...
&& apt-get install -y --no-install-recommends docker-ce-cli \

# 修复后
COPY . /app/PPTAgent
...
# NOTE: Docker CLI will be mounted from host at runtime
# 不再安装 Docker CLI，避免网络下载问题
```

**改进优势**：
- ✅ 避免 GPG 密钥下载失败（网络问题）
- ✅ 与宿主机 Docker daemon 版本完全匹配（CentOS 7 上的 20.10.x）
- ✅ 减少构建时间（不需要添加 Docker 仓库）
- ✅ 减少镜像体积（不安装额外的 docker-ce-cli 包）

---

### 2. Makefile 修复

**文件**: `F:/dense/PPTAgent/Makefile`

**修复内容**：
- ✅ 第 100 行：删除 `--build-arg CACHE_DATE`（消除警告）
- ✅ 第 113 行：删除 `--build-arg CACHE_DATE`（docker-rebuild）
- ✅ 第 141、166 行：添加 Docker CLI 挂载 `-v /usr/bin/docker:/usr/bin/docker:ro`
- ✅ 第 142、167 行：添加代码挂载 `-v $(pwd):/app/PPTAgent`

```makefile
# 修复前
docker build --build-arg CACHE_DATE="$(date +%Y%m%d_%H%M%S)" ...
-v $(HOME)/.cache/huggingface:/root/.cache/huggingface \

# 修复后
docker build -t pptagent-complete:latest ...
-v /var/run/docker.sock:/var/run/docker.sock \
-v /usr/bin/docker:/usr/bin/docker:ro \
-v $(pwd):/app/PPTAgent \
-v $$HOME/.cache/huggingface:/root/.cache/huggingface \
```

---

### 3. mcp.json 修复

**文件**: `F:/dense/PPTAgent/deeppresenter/deeppresenter/mcp.json`

**修复内容**：
- ✅ 第 8 行：路径修正为 `deeppresenter/deeppresenter/tools/server.py`（两层 deeppresenter）

```json
// 修复前
"args": ["run", "deeppresenter/tools/server.py", "$WORKSPACE"]

// 修复后
"args": ["run", "deeppresenter/deeppresenter/tools/server.py", "$WORKSPACE"]
```

---

### 4. PPTAgent.yaml 修复

**文件**: `F:/dense/PPTAgent/deeppresenter/deeppresenter/roles/PPTAgent.yaml`

**修复内容**：
- ✅ 第 36 行：`use_model` 改为 `design_agent`（修复配置错误）

```yaml
# 修复前
use_model: agent  # ❌ config.yaml 中不存在

# 修复后
use_model: design_agent  # ✅ 正确配置
```

---

### 5. Dockerfile 依赖安装修复

**文件**: `F:/dense/PPTAgent/Dockerfile`

**修复内容**：
- ✅ 第 46-48 行：显式安装 pptagent（修复 `ModuleNotFoundError: No module named 'pptx'`）

```dockerfile
# 修复前
RUN uv pip install --system -e ./deeppresenter && \
    uv pip install --system playwright

# 修复后
RUN uv pip install --system -e ./pptagent && \
    uv pip install --system -e ./deeppresenter && \
    uv pip install --system playwright
```

**问题原因**：
- `deeppresenter/tools/task.py` 需要导入 `pptx` 模块
- 依赖链：`deeppresenter` → `pptagent>=0.2.16` → `pptagent-pptx>=0.0.1`
- 可编辑模式（`-e`）安装时，级联依赖可能不完整
- 显式安装 pptagent 确保所有依赖正确安装

---

## 完整部署步骤

### 前置条件

确保已准备好以下内容：

- [ ] Docker 已安装（版本 >= 20.10）
- [ ] 项目代码在 `F:/dense/PPTAgent`
- [ ] API Keys 已申请：
  - [ ] OpenAI/硅基流动 API Key
  - [ ] Tavily API Key
  - [ ] MinerU API Key（可选）

---

### 步骤 1：配置环境变量

#### 1.1 创建 .env 文件

```bash
cd /f/dense/PPTAgent
make setup-env
```

#### 1.2 编辑 .env 文件

```bash
vim .env
```

**填入以下内容**：

```bash
# LLM API 配置
OPENAI_API_KEY=sk-your-siliconflow-key
API_BASE=https://api.siliconflow.cn/v1
LANGUAGE_MODEL=Qwen/Qwen2.5-72B-Instruct
VISION_MODEL=Qwen/Qwen2-VL-72B-Instruct

# 搜索 API（必需）
TAVILY_API_KEY=tvly-your-tavily-key

# PDF 解析（可选）
MINERU_API=http://localhost:8000/file_parse
```

#### 1.3 配置 config.yaml

```bash
vim deeppresenter/deeppresenter/config.yaml
```

**填入以下内容**：

```yaml
research_agent:
  base_url: "https://api.siliconflow.cn/v1"
  model: "Qwen/Qwen2.5-72B-Instruct"
  api_key: "sk-your-siliconflow-key"

design_agent:
  base_url: "https://api.siliconflow.cn/v1"
  model: "Qwen/Qwen2.5-72B-Instruct"
  api_key: "sk-your-siliconflow-key"

long_context_model:
  base_url: "https://api.siliconflow.cn/v1"
  model: "deepseek-ai/DeepSeek-V3"
  api_key: "sk-your-siliconflow-key"

vision_model:
  base_url: "https://api.siliconflow.cn/v1"
  model: "Qwen/Qwen2-VL-72B-Instruct"
  api_key: "sk-your-siliconflow-key"

t2i_model:
  base_url: "https://api.siliconflow.cn/v1"
  model: "stabilityai/stable-diffusion-3-5-large"
  api_key: "sk-your-siliconflow-key"
  sampling_parameters:
    response_format: "b64_json"
    extra_body: { "watermark": false }
```

#### 1.4 验证 mcp.json 配置

```bash
vim deeppresenter/deeppresenter/mcp.json
```

**确认以下配置正确**：

```json
[
    {
        "name": "deeppresenter",
        "args": [
            "run",
            "deeppresenter/deeppresenter/tools/server.py",
            "$WORKSPACE"
        ],
        "env": {
            "TAVILY_API_KEY": "tvly-your-tavily-key",
            "MIN_IMAGE_SIZE": "921600"
        }
    },
    {
        "name": "pptagent",
        "args": ["run", "pptagent-mcp"],
        "env": {
            "PPTAGENT_MODEL": "Qwen/Qwen2.5-72B-Instruct",
            "PPTAGENT_API_KEY": "sk-your-siliconflow-key",
            "PPTAGENT_API_BASE": "https://api.siliconflow.cn/v1"
        }
    },
    {
        "name": "desktop_commander",
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

---

### 步骤 2：构建 Docker 镜像

#### 2.1 构建主容器镜像

```bash
cd /f/dense/PPTAgent
make docker-build
```

**预计耗时**: 8-12 分钟

**期望输出**：
```
构建 PPTAgent 主容器镜像...
⚠️  此过程可能需要 10-20 分钟，请耐心等待...
[+] Building 480.5s (12/12) FINISHED
 => [1/8] FROM python:3.11-slim
 => [2/8] COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
 => [3/8] WORKDIR /app
 => [4/8] RUN apt-get update && apt-get install -y ...
 => [5/8] COPY . /app/PPTAgent
 => [6/8] WORKDIR /app/PPTAgent
 => [7/8] RUN uv pip install --system -e ./deeppresenter
 => [8/8] RUN playwright install chromium
 => exporting to image
 => => naming to docker.io/library/pptagent-complete:latest
✅ 镜像构建完成：pptagent-complete:latest
```

**构建成功标志**：
- ✅ 看到 `Successfully built`
- ✅ 看到 `Successfully tagged pptagent-complete:latest`
- ✅ 无 `[Warning] build-args` 警告

#### 2.2 构建沙盒镜像

```bash
cd /f/dense/PPTAgent
make build-sandbox
```

**预计耗时**: 3-5 分钟

**期望输出**：
```
构建 deeppresenter 沙盒容器...
[+] Building 120.3s (8/8) FINISHED
✅ 沙盒容器构建完成：desktop-commander-deeppresenter
```

#### 2.3 验证镜像

```bash
make version
```

**期望输出**：
```
PPTAgent 版本信息：

Docker 镜像：
pptagent-complete                latest    abc123def456   2 minutes ago    3.5GB
desktop-commander-deeppresenter  latest    def456abc123   1 minute ago     1.2GB

Docker 版本：
Docker version 20.10.x, build xxxxx

容器状态：
  容器不存在
```

---

### 步骤 3：启动服务

#### 3.1 启动容器

```bash
cd /f/dense/PPTAgent
make docker-run-cpu
```

**期望输出**：
```
启动 PPTAgent 容器（CPU 模式）...
检查环境变量...
✅ OPENAI_API_KEY: sk-cjcigu...
✅ TAVILY_API_KEY: tvly-dev-C...
abc123def456789...
✅ 容器已启动（CPU 模式）
访问 http://localhost:7861 使用 Web UI
```

#### 3.2 查看启动日志

```bash
make docker-logs
```

**期望输出**：

```
* Running on local URL:  http://0.0.0.0:7861
INFO - 6 templates loaded successfully: thu, beamer, hit, default, cip, ucas
INFO - Starting MCP server 'PPTAgent' with transport 'stdio'
INFO - Connected to server deeppresenter.
INFO - Connected to server desktop_commander.
INFO - Connected to server pptagent.
```

**关键检查点**：
- ✅ `Running on local URL: http://0.0.0.0:7861` - Web UI 启动成功
- ✅ `6 templates loaded successfully` - pptagent MCP server 启动成功
- ✅ `Connected to server deeppresenter` - deeppresenter server 启动成功
- ✅ `Connected to server desktop_commander` - Docker 沙盒连接成功
- ✅ `Connected to server pptagent` - pptagent MCP server 连接成功

#### 3.3 验证容器运行

```bash
docker ps | grep pptagent
```

**期望输出**：
```
abc123def456  pptagent-complete:latest  "python webui.py 0.0…"  2 minutes ago  Up 2 minutes  pptagent
```

---

### 步骤 4：访问 Web UI

#### 4.1 打开浏览器

访问：http://localhost:7861

#### 4.2 界面检查

- ✅ 页面正常加载，无 404 错误
- ✅ 标题显示 "DeepPresenter"
- ✅ 有两个模式选择：
  - "自由生成 (freeform)"
  - "模版 (templates)"
- ✅ 模板选择下拉框有以下选项：
  - auto
  - default
  - beamer
  - cip
  - hit
  - thu
  - ucas
- ✅ 页数选择：4, 6, 8, 10, 12, 14, 16

---

### 步骤 5：功能测试

#### 5.1 测试模版模式

**操作步骤**：

1. **选择模式**：切换到"模版 (templates)"
2. **选择模板**：选择 "default"
3. **选择页数**：选择 "6"
4. **上传文件**：点击"上传附件"，上传一个 Markdown 或 PDF 文件
5. **输入指令**：输入"请根据上传的文件生成 PPT"
6. **发送请求**：点击"发送"按钮

**预期日志输出**：

```bash
make docker-logs | tail -50
```

```
⚙️ System Message
DeepPresenter running in /root/.cache/deeppresenter/xxxxx, with 1 attachments

🤖 Assistant Message
[Research Agent 工作]
正在分析文档...
正在搜索相关资料...

📝 Tool
{"name": "tavily_search", "arguments": {...}}

🤖 Assistant Message
[PPTAgent Agent 工作]
正在生成幻灯片...

📝 Tool
{"name": "set_template", "arguments": {"template_name": "default"}}

📝 Tool
{"name": "create_slide", "arguments": {"layout": "title_layout"}}

📝 Tool
{"name": "generate_slide", "arguments": {}}

[重复多次...]

📄 幻灯片生成完成，点击下方按钮下载文件
```

**下载并验证**：

7. **下载文件**：点击"Download"按钮
8. **打开 PPTX**：使用 PowerPoint/LibreOffice 打开
9. **验证内容**：
   - ✅ 幻灯片数量正确（6页）
   - ✅ 模板样式正确（default 样式）
   - ✅ 内容与上传文件相关
   - ✅ 布局合理，无乱码

---

#### 5.2 测试自由生成模式（可选）

**操作步骤**：

1. **选择模式**：切换到"自由生成 (freeform)"
2. **输入指令**：输入"生成一个关于人工智能发展历程的演示文稿，包含5页"
3. **发送请求**：点击"发送"按钮

**预期流程**：

```
Research Agent 搜索 → Design Agent 设计 → 生成 PDF
```

**验证**：
- ✅ Research Agent 执行搜索
- ✅ Design Agent 生成 HTML/CSS
- ✅ 转换为 PDF 文件
- ✅ 下载并打开 PDF 验证

---

## 常见问题排查

### 问题 1：MCP Server 连接失败

**症状**：
```
ERROR: Error connecting to server deeppresenter: Connection closed
ERROR: Error connecting to server desktop_commander: Connection closed
```

**排查步骤**：

1. **检查路径是否正确**：
```bash
docker exec pptagent ls -la /app/PPTAgent/deeppresenter/deeppresenter/tools/server.py
```

2. **检查 Docker CLI 版本**：
```bash
docker exec pptagent docker --version
# 应该输出：Docker version 20.10.x
```

3. **测试 Docker 通信**：
```bash
docker exec pptagent docker ps
# 应该能看到容器列表
```

4. **手动测试 MCP server**：
```bash
docker exec pptagent uv run deeppresenter/deeppresenter/tools/server.py /tmp
```

---

### 问题 2：Web UI 无法访问

**症状**：浏览器访问 http://localhost:7861 显示无法连接

**排查步骤**：

1. **检查容器是否运行**：
```bash
docker ps | grep pptagent
```

2. **检查端口映射**：
```bash
docker port pptagent
# 应该输出：7861/tcp -> 0.0.0.0:7861
```

3. **检查端口是否被占用**：
```bash
netstat -tuln | grep 7861
# 或 Windows 上：
netstat -ano | findstr 7861
```

4. **查看完整日志**：
```bash
make docker-logs | grep -E "Running on|ERROR"
```

5. **进入容器测试**：
```bash
docker exec pptagent curl http://localhost:7861
```

---

### 问题 3：生成 PPT 失败

**症状**：点击发送后报错或无响应

**排查步骤**：

1. **检查 API Keys**：
```bash
docker exec pptagent env | grep API_KEY
# 验证 keys 是否正确设置
```

2. **测试模型连接**：
```bash
docker exec pptagent python3 -c "
from pptagent.llms import LLM
llm = LLM('Qwen/Qwen2.5-72B-Instruct', 'https://api.siliconflow.cn/v1', 'sk-xxx')
print(llm('测试'))
"
```

3. **查看详细错误**：
```bash
make docker-logs | tail -200
```

4. **验证 MCP servers 状态**：
```bash
make docker-logs | grep "Connected to server"
# 应该看到 3 个 servers 都连接成功
```

---

## 维护操作

### 重启容器

```bash
make docker-restart
```

**何时使用**：
- 修改了 `.env` 文件
- 修改了 `config.yaml`
- 修改了 `mcp.json`
- 修改了 Python 代码（已挂载）

---

### 重新构建镜像

```bash
make docker-clean
make docker-build
make docker-run-cpu
```

**何时使用**：
- 修改了 `Dockerfile`
- 修改了 `pyproject.toml`（依赖变化）
- 需要更新系统包

---

### 查看日志

```bash
# 实时日志
make docker-logs

# 最近 100 行
make docker-logs | tail -100

# 搜索错误
make docker-logs | grep ERROR

# 搜索特定 MCP server
make docker-logs | grep "pptagent"
```

---

### 进入容器调试

```bash
make docker-shell

# 在容器内执行
cd /app/PPTAgent
python webui.py 0.0.0.0  # 手动启动
uv run pptagent-mcp      # 测试 pptagent MCP server
ls -la deeppresenter/deeppresenter/tools/  # 验证文件
```

---

### 清理资源

```bash
# 停止并删除容器
make docker-clean

# 清理所有 Docker 资源（镜像、容器、缓存）
make clean-all

# 清理 Python 缓存
make clean
```

---

## 更新配置（无需重新构建）

### 更新 API Keys

```bash
# 1. 编辑配置
vim .env
vim deeppresenter/deeppresenter/config.yaml
vim deeppresenter/deeppresenter/mcp.json

# 2. 重启容器
make docker-restart

# 3. 验证生效
make docker-logs | grep "Connected to server"
```

### 更新模型配置

```bash
# 1. 编辑 config.yaml
vim deeppresenter/deeppresenter/config.yaml

# 修改模型（例如从 Qwen 换到 DeepSeek）
# research_agent:
#   model: "deepseek-ai/DeepSeek-V3"

# 2. 重启容器
make docker-restart
```

### 更新代码

```bash
# 1. 修改代码
vim pptagent/pptagent/pptgen.py

# 2. 重启容器（代码已挂载，立即生效）
make docker-restart

# 3. 验证
make docker-logs
```

---

## 性能优化建议

### 1. 使用 GPU 加速（可选）

如果有 GPU：

```bash
# 使用 GPU 模式启动
make docker-run
```

### 2. 缓存模型

```bash
# Makefile 已配置缓存挂载
-v $HOME/.cache/huggingface:/root/.cache/huggingface
```

### 3. 并行处理

在 `config.yaml` 中使用快速模型：

```yaml
design_agent:
  model: "Qwen/Qwen2.5-32B-Instruct"  # 更快
  # 而不是 72B
```

---

## 部署成功检查清单

完成部署后，确认以下检查项：

- [ ] **Docker 镜像**
  - [ ] `pptagent-complete:latest` 已构建（约 3-5GB）
  - [ ] `desktop-commander-deeppresenter` 已构建（约 1-2GB）

- [ ] **容器运行**
  - [ ] `docker ps` 可以看到 pptagent 容器
  - [ ] 容器状态为 "Up"

- [ ] **MCP Servers**
  - [ ] pptagent server 启动成功（6 templates loaded）
  - [ ] deeppresenter server 连接成功
  - [ ] desktop_commander 连接成功

- [ ] **Web UI**
  - [ ] http://localhost:7861 可以访问
  - [ ] 界面正常显示
  - [ ] 模板下拉框有选项

- [ ] **功能测试**
  - [ ] 可以上传文件
  - [ ] 可以生成 PPT
  - [ ] 可以下载 PPTX 文件
  - [ ] PPTX 文件可以正常打开

---

## 技术支持

**问题反馈**：
- GitHub Issues: https://github.com/icip-cas/PPTAgent/issues
- 故障排查文档: `F:/dense/docs/pptagent_deployment_troubleshooting.md`

**相关文档**：
- `Makefile` - 完整命令列表
- `CLAUDE.md` - 项目架构说明
- `pptagent/DOC.md` - PPTAgent 核心文档
- `deeppresenter/README.md` - DeepPresenter 文档

---

**部署指南结束**

祝部署成功！🎉
