# syntax=docker/dockerfile:1.7
FROM node:lts-bullseye-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV MCP_CLIENT_DOCKER=true

WORKDIR /usr/src/app

RUN sed -i 's|http://deb.debian.org/debian|http://mirrors.tuna.tsinghua.edu.cn/debian|g' /etc/apt/sources.list && \
    sed -i 's|http://deb.debian.org/debian-security|http://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list && \
    sed -i 's|http://security.debian.org/debian-security|http://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update --allow-insecure-repositories && \
    apt-get install -y --fix-missing --no-install-recommends --allow-unauthenticated ca-certificates && \
    update-ca-certificates && \
    apt-get install -y --no-install-recommends git bash

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Copy local DesktopCommanderMCP repository
COPY DesktopCommanderMCP/ .

RUN --mount=type=cache,target=/root/.npm \
    npm install --ignore-scripts

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get install -y --no-install-recommends curl wget unzip ripgrep vim sudo g++ locales

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen

ENV PATH="/opt/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium \
    CHROME_PATH=/usr/bin/chromium \
    VIRTUAL_ENV="/opt/.venv" \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    MPLCONFIGDIR=/etc/matplotlib

# Puppeteer config for mermaid-cli
RUN echo '{"args":["--no-sandbox","--disable-setuid-sandbox"]}' > /root/.puppeteerrc.json

# Export ENV to /etc/profile.d/ for bash -lc and interactive shells
RUN printenv | grep -E '^(PATH|PYTHONUNBUFFERED|VIRTUAL_ENV|PUPPETEER_|CHROME_|LANG|LC_ALL|MPLCONFIGDIR|MCP_CLIENT_DOCKER)=' | sed 's/^/export /' > /etc/profile.d/docker-env.sh && \
    echo 'source /etc/profile.d/docker-env.sh' >> /etc/bash.bashrc

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

COPY deeppresenter/docker/SandBox/config.json /root/.claude-server-commander/config.json
COPY deeppresenter/docker/SandBox/server.ts src/server.ts
COPY deeppresenter/docker/SandBox/improved-process-tools.ts src/tools/improved-process-tools.ts

RUN fc-cache -f && \
    mkdir -p /etc/matplotlib && \
    printf '%s\n' \
      'font.family: sans-serif' \
      'font.sans-serif: Noto Sans CJK SC, WenQuanYi Zen Hei, DejaVu Sans' \
      > /etc/matplotlib/matplotlibrc

RUN npm run build

CMD ["node",  "/usr/src/app/dist/index.js", "--no-onboarding"]
