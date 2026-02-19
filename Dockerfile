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
    tini \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY backend ./backend

# Frontend runtime (includes node_modules + .next from build stage)
COPY --from=web-build /app/frontend /app/frontend

COPY run_linux.sh /app/run_linux.sh

# Remove CRLF if the repo was edited on Windows
RUN sed -i 's/\r$//' /app/run_linux.sh \
  && chmod +x /app/run_linux.sh

EXPOSE 3000

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/app/run_linux.sh", "--docker"]
