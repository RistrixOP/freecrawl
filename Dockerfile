FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates fonts-liberation \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxrandr2 libgbm1 libasound2 libpangocairo-1.0-0 \
    xvfb dbus \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# Install patchright browsers
RUN patchright install chromium

# Xvfb for non-headless anti-bot mode
ENV DISPLAY=:99

EXPOSE 9100

# Start Xvfb + server
CMD ["sh", "-c", "Xvfb :99 -screen 0 1920x1080x24 & sleep 1 && python -m freecrawl serve --host 0.0.0.0 --port 9100"]
