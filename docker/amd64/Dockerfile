# Using nikolaik/python-nodejs for Python 3.11 + Node.js 20 support

FROM nikolaik/python-nodejs:python3.11-nodejs20-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright \
    HF_ENDPOINT=https://hf-mirror.com \
    HF_HOME=/root/.cache/huggingface

WORKDIR /app

# ==============================================================================
# Layer 1: Install system dependencies with apt cache mount
# ==============================================================================
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    chromium \
    libreoffice \
    poppler-utils \
    curl \
    wget \
    ca-certificates \
    jq \
    vim

# ==============================================================================
# Layer 2: Copy project files
# ==============================================================================
WORKDIR /app/PPTAgent
COPY ../.. /app/PPTAgent

# ==============================================================================
# Layer 3: Install Node.js and Python dependencies with cache mounts
# ==============================================================================
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=cache,target=/root/.cache/pip \
    npm install && \
    uv pip install --system -e ./deeppresenter && \
    playwright install chromium && \
    playwright install-deps chromium

# ==============================================================================
# Layer 5: Pre-download HuggingFace models with HF cache mount
# ==============================================================================
RUN --mount=type=cache,target=/root/.cache/huggingface \
    hf download julien-c/fasttext-language-id || \
      echo "Warning: Failed to download fasttext model" ; \
    hf download google/vit-base-patch16-224-in21k || \
      echo "Warning: Failed to download ViT model"

CMD ["python", "webui.py", "0.0.0.0"]
