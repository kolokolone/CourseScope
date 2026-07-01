# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS web-build
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Audit de sécurité read-only : ne pas retirer les devDependencies avant le build.
RUN npm audit --omit=dev --audit-level=critical || exit 1

ENV NEXT_TELEMETRY_DISABLED=1

COPY frontend ./
RUN npm run build


FROM python:3.13-slim-bookworm

WORKDIR /app

ENV NODE_ENV=production \
    COURSESCOPE_DATA_DIR=/data \
    DEBIAN_FRONTEND=noninteractive \
    NEXT_TELEMETRY_DISABLED=1

# Install Node.js 22 via NodeSource
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    tini \
  && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
  && apt-get install -y --no-install-recommends nodejs \
  && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY VERSION ./
COPY backend ./backend

# Frontend runtime (standalone : only compiled code + static assets + public)
COPY --from=web-build /app/frontend/.next/standalone /app/frontend
COPY --from=web-build /app/frontend/.next/static /app/frontend/.next/static
COPY --from=web-build /app/frontend/public /app/frontend/public

COPY run_linux.sh /app/run_linux.sh

# Remove CRLF if the repo was edited on Windows
RUN sed -i 's/\r$//' /app/run_linux.sh \
  && chmod +x /app/run_linux.sh

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/app/run_linux.sh", "--docker"]
