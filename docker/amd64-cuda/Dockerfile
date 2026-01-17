# CUDA-enabled version for GPU acceleration
# Base image: CUDA 12.1 + cuDNN 8 on Ubuntu 22.04

FROM nvidia/cuda:12.1.0-cudnn8-devel-ubuntu22.04
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright \
    HF_ENDPOINT=https://hf-mirror.com \
    HF_HOME=/root/.cache/huggingface \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    CUDA_HOME=/usr/local/cuda \
    PATH=/usr/local/cuda/bin:${PATH} \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH}

WORKDIR /app

# ==============================================================================
# Layer 1: Install Python 3.11 with apt cache mount
# ==============================================================================
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    curl \
    wget \
    ca-certificates \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3.11-distutils \
    python3-pip \
    chromium-browser \
    libreoffice \
    poppler-utils \
    jq \
    vim \
    git \
    locales \
    && locale-gen en_US.UTF-8 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && python3 --version

# ==============================================================================
# Layer 1.5: Install Node.js 22 from NodeSource
# ==============================================================================
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && node --version \
    && npm --version

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
    UV_HTTP_TIMEOUT=600 uv pip install --system -e ./deeppresenter && \
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
