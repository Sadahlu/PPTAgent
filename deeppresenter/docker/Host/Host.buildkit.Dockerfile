FROM node:lts-bullseye-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8 \
    PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright \
    HF_ENDPOINT=https://hf-mirror.com \
    HF_HOME=/root/.cache/huggingface \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/.venv/bin:${PATH}" \
    VIRTUAL_ENV="/opt/.venv" \
    DEEPPRESENTER_WORKSPACE_BASE="/opt/workspace"

RUN sed -i 's|http://deb.debian.org/debian|http://mirrors.tuna.tsinghua.edu.cn/debian|g' /etc/apt/sources.list && \
    sed -i 's|http://deb.debian.org/debian-security|http://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list && \
    sed -i 's|http://security.debian.org/debian-security|http://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list

# ==============================================================================
# Layer 1: Install ca-certificates first to avoid GPG signature issues, then other packages
# ==============================================================================
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update --allow-insecure-repositories && \
    apt-get install -y --fix-missing --no-install-recommends --allow-unauthenticated ca-certificates && \
    update-ca-certificates && \
    apt-get install -y --no-install-recommends git bash curl wget unzip ripgrep vim sudo g++ gcc locales make jq

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen

# ==============================================================================
# Layer 2: Install Chromium and other dependencies
# ==============================================================================
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --fix-missing --no-install-recommends \
    chromium \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    imagemagick \
    libreoffice \
    poppler-utils

# ==============================================================================
# Layer 3: Install fonts and refresh font cache
# ==============================================================================
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get install -y --no-install-recommends \
    fonts-noto-cjk \
    fonts-noto-cjk-extra \
    fonts-wqy-zenhei \
    fonts-wqy-microhei && \
    fc-cache -f

# ==============================================================================
# Layer 4: Copy project files
# ==============================================================================
WORKDIR /app/PPTAgent
COPY . /app/PPTAgent

# ==============================================================================
# Layer 5: Install Node.js dependencies
# ==============================================================================
RUN --mount=type=cache,target=/root/.npm \
    npm install --ignore-scripts && \
    npx playwright install chromium

# ==============================================================================
# Layer 6: Create Python virtual environment and install dependencies
# ==============================================================================
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv --python 3.13 $VIRTUAL_ENV && \
    uv pip install -e ./deeppresenter

# ==============================================================================
# Layer 7: Pre-download HuggingFace models with HF cache mount
# ==============================================================================
RUN --mount=type=cache,target=/root/.cache/huggingface \
    hf download julien-c/fasttext-language-id || \
      echo "Warning: Failed to download fasttext model" ; \
    hf download google/vit-base-patch16-224-in21k || \
      echo "Warning: Failed to download ViT model"

CMD ["bash", "-c", "umask 000 && python webui.py 0.0.0.0"]
