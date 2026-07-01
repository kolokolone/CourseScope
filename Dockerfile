# syntax=docker/dockerfile:1

FROM node:20-bookworm-slim AS web-build
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./
RUN npm run build


FROM node:20-bookworm-slim

WORKDIR /app

ENV NODE_ENV=production \
    COURSESCOPE_DATA_DIR=/data

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    tini \
    curl \
  && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY VERSION ./
COPY backend ./backend

# Frontend runtime (includes node_modules + .next from build stage)
COPY --from=web-build /app/frontend /app/frontend

COPY run_linux.sh /app/run_linux.sh

# Remove CRLF if the repo was edited on Windows
RUN sed -i 's/\r$//' /app/run_linux.sh \
  && chmod +x /app/run_linux.sh

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/app/run_linux.sh", "--docker"]
