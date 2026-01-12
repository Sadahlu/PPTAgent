# uv 和 uv.lock 说明

## 什么是 uv？

`uv` 是 Astral 团队（ruff 的作者）开发的**极快的 Python 包管理器**，用 Rust 编写。

### 性能对比

| 工具 | 安装速度 | 依赖解析 |
|------|---------|---------|
| pip | 基准 | 慢 |
| poetry | 2-3x | 慢 |
| **uv** | **10-100x** | **极快** |

### 在 PPTAgent 中的使用

#### 1. Docker 镜像构建（`pptagent/docker/Dockerfile`）

```dockerfile
# 第 2 行：从官方镜像复制 uv 工具
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 使用 uv 替代 pip，大幅加速构建
RUN uv pip install --system huggingface_hub
RUN uv pip install --system "pptagent[full]"
```

#### 2. MCP Server（`pptagent/DOC.md`）

```bash
# 使用 uv 安装和运行
uv pip install pptagent
uv run pptagent-mcp
```

#### 3. 后端启动（`pptagent/docker/launch.sh`）

```bash
# 使用 uv run 而不是 python
uv run backend.py &
```

## uv.lock 文件

### 作用

`uv.lock` 是**依赖锁定文件**，类似于：
- `package-lock.json`（npm）
- `poetry.lock`（poetry）
- `Pipfile.lock`（pipenv）

### 内容

```toml
version = 1
requires-python = ">=3.11"

[[package]]
name = "pptagent"
version = "0.2.16"
dependencies = [
    "openai>=1.108.2",
    "pydantic>=2.10.0",
    # ... 精确版本锁定
]
```

### 好处

1. **可重复构建**：确保所有环境安装相同版本
2. **依赖完整性**：记录所有传递依赖
3. **快速安装**：uv 使用 lock 文件跳过依赖解析
4. **多平台支持**：包含 resolution-markers 处理不同平台

### PPTAgent 中的 uv.lock

```bash
ls -lh pptagent/uv.lock deeppresenter/uv.lock
# pptagent/uv.lock:      738 KB  # 约 300+ 个依赖包
# deeppresenter/uv.lock: 724 KB  # 约 400+ 个依赖包
```

## 开发者如何使用

### 方式 1：使用 pip（传统，兼容性好）

```bash
pip install -e pptagent
pip install -e deeppresenter
```

### 方式 2：使用 uv（推荐，速度快）

```bash
# 安装 uv
pip install uv
# 或：curl -LsSf https://astral.sh/uv/install.sh | sh

# 使用 uv 安装（利用 uv.lock）
uv pip install -e pptagent
uv pip install -e deeppresenter

# 运行脚本
uv run python script.py
```

### 方式 3：使用 Docker（无需关心 uv）

```bash
# Docker 镜像内部已集成 uv
docker pull forceless/pptagent:latest
docker run -dt -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -p 8088:8088 forceless/pptagent
```

## 自定义构建镜像

### 使用 pptagent/docker/Dockerfile

```bash
# 克隆仓库
git clone https://github.com/icip-cas/PPTAgent
cd PPTAgent

# 修改 Dockerfile（可选）
vim pptagent/docker/Dockerfile

# 构建自定义镜像
cd pptagent/docker
docker build -t my-pptagent:custom .

# 运行自定义镜像
docker run -dt -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -p 8088:8088 my-pptagent:custom
```

### 使用场景

**何时需要自己构建**：
- 修改依赖版本
- 添加自定义系统包
- 更改 Python 版本
- 添加自定义模型
- 优化镜像大小

**何时使用预构建镜像**：
- 快速部署
- 标准功能
- 不需要定制

## 总结

| 组件 | 作用 | 用户是否需要 |
|------|------|------------|
| `uv` 工具 | 快速包管理器 | 可选（pip 也可以） |
| `uv.lock` | 锁定依赖版本 | 自动使用（透明） |
| `pptagent/docker/Dockerfile` | 构建应用镜像 | 可选（有预构建镜像） |
| `forceless/pptagent:latest` | 预构建镜像 | 推荐使用 |

**推荐方式**：
- **快速体验**：使用预构建镜像 `forceless/pptagent:latest`
- **本地开发**：使用 `pip install -e` 或 `uv pip install -e`
- **定制需求**：修改并构建 `pptagent/docker/Dockerfile`

## 常见问题

**Q: 我可以不用 uv，只用 pip 吗？**
A: 可以！`pip install -e pptagent` 完全兼容。uv 只是可选的加速工具。

**Q: uv.lock 文件我需要修改吗？**
A: 不需要。它由 uv 自动生成和管理。手动修改可能导致错误。

**Q: 为什么有两个 uv.lock？**
A: `pptagent/uv.lock` 和 `deeppresenter/uv.lock` 分别对应两个包的依赖。

**Q: Docker 镜像为什么用 uv？**
A: 大幅减少构建时间。安装 300+ 包从几分钟降到几十秒。
