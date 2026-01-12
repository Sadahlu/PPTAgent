# PPTAgent Minimal Dockerfile
# Optimized for web service deployment

FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright


WORKDIR /app

# Install minimal system dependencies
# NOTE: Docker CLI will be mounted from host at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    gcc \
    g++ \
    make \
    git \
    # Document processing (LibreOffice for PPTX conversion)
    libreoffice \
    # PDF utilities
    poppler-utils \
    # Common utilities
    curl \
    wget \
    ca-certificates \
    jq \
    vim \
    # Final cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy local project files
COPY . /app/PPTAgent

# Install Python packages
WORKDIR /app/PPTAgent
RUN uv pip install --system -e ./deeppresenter && \
    uv pip install --system playwright

# Install Playwright browsers and system dependencies
RUN playwright install chromium && \
    playwright install-deps chromium

# Create cache directories
RUN mkdir -p /root/.cache/huggingface && \
    mkdir -p /root/.cache/deeppresenter

# Expose ports
# 7861: Gradio WebUI (default port in webui.py)
# 9297: Backend API (optional)
EXPOSE 7861 9297

# Default command
# Note: webui.py accepts server_name as first positional argument
CMD ["python", "webui.py", "0.0.0.0"]
