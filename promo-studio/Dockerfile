# Playwright 官方映像已含 Chromium 與所需系統套件
FROM mcr.microsoft.com/playwright:v1.63.0-noble
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-noto-cjk fonts-noto-color-emoji && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY package*.json ./
RUN PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm ci --omit=dev || PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install --omit=dev
COPY . .
ENV PORT=3000 NODE_ENV=production
EXPOSE 3000
CMD ["node", "server.js"]
