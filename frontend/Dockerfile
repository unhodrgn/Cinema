FROM node:24-bookworm-slim AS build
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci --no-fund --no-audit
COPY frontend ./
RUN npm run build && npm run build:legacy

FROM python:3.12-slim-bookworm
WORKDIR /ui
COPY --from=build /ui/dist dist
COPY --from=build /ui/dist-legacy dist-legacy
COPY frontend/server.py .
CMD ["python", "server.py"]
