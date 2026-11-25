FROM node:24-trixie-slim AS build
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci --no-fund --no-audit
COPY frontend ./
RUN npm run build && npm run build:legacy

FROM python:3.12-slim-trixie
WORKDIR /ui
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 --shell /usr/sbin/nologin cinema
COPY --from=build --chown=cinema:cinema /ui/dist dist
COPY --from=build --chown=cinema:cinema /ui/dist-legacy dist-legacy
COPY --chown=cinema:cinema frontend/server.py .
USER cinema
CMD ["python", "server.py"]
