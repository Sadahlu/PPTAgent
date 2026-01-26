# syntax=docker/dockerfile:1.7
FROM node:lts-bullseye-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV MCP_CLIENT_DOCKER=true

WORKDIR /usr/src/app

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update --allow-insecure-repositories && \
    apt-get install -y --fix-missing --no-install-recommends --allow-unauthenticated ca-certificates && \
    update-ca-certificates && \
    apt-get install -y --no-install-recommends git bash

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN git clone https://github.com/wonderwhy-er/DesktopCommanderMCP.git . && \
    git checkout 252a00d624c2adc5707fa743c57a1b68bc223689 && \
    rm -rf .git

RUN --mount=type=cache,target=/root/.npm \
    npm install --ignore-scripts

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get install -y --no-install-recommends curl wget unzip ripgrep vim

ENV PATH="/opt/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium \
    CHROME_PATH=/usr/bin/chromium \
    VIRTUAL_ENV="/opt/.venv"

RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv --python 3.13 $VIRTUAL_ENV && \
    uv pip install pip python-pptx matplotlib seaborn plotly numpy pandas opencv-python-headless pillow html2image

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get install -y --no-install-recommends \
        chromium fonts-liberation libappindicator3-1 libasound2 libatk-bridge2.0-0 libatk1.0-0 libcups2 libdbus-1-3 libdrm2 libgbm1 libgtk-3-0 libnspr4 libnss3 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 xdg-utils \
        fonts-dejavu fonts-noto fonts-noto-cjk fonts-noto-cjk-extra fonts-noto-color-emoji fonts-freefont-ttf fonts-urw-base35 fonts-roboto fonts-wqy-zenhei fonts-wqy-microhei fonts-arphic-ukai fonts-arphic-uming fonts-ipafont fonts-ipaexfont fonts-comic-neue \
        imagemagick

RUN --mount=type=cache,target=/root/.npm \
    npm install -g @mermaid-js/mermaid-cli pptxgenjs playwright sharp react react-dom react-icons

RUN npx playwright install chromium

COPY config.json /root/.claude-server-commander/config.json
COPY server.ts src/server.ts
COPY improved-process-tools.ts src/tools/improved-process-tools.ts

ENV MPLCONFIGDIR=/etc/matplotlib
RUN fc-cache -f && \
    mkdir -p /etc/matplotlib && \
    printf '%s\n' \
      'font.family: sans-serif' \
      'font.sans-serif: Noto Sans CJK SC, WenQuanYi Zen Hei, DejaVu Sans' \
      > /etc/matplotlib/matplotlibrc

RUN npm run build

CMD ["node",  "/usr/src/app/dist/index.js", "--no-onboarding"]
