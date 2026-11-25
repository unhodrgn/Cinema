FROM python:3.12-slim-trixie AS dependencies
WORKDIR /cinema/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

FROM dependencies AS runtime
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 --shell /usr/sbin/nologin cinema
COPY --chown=cinema:cinema backend/app app
COPY --chown=cinema:cinema backend/scripts scripts
COPY --chown=cinema:cinema backend/seeds seeds
COPY --chown=cinema:cinema backend/migrations migrations
USER cinema
CMD ["python", "-m", "flask", "--app", "app.main:create_app", "run", "--no-reload", "--host", "0.0.0.0", "--port", "5000"]

FROM node:24-trixie-slim AS node
FROM dependencies AS verify
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && apt-get install -y --no-install-recommends postgresql-client chromium-headless-shell \
 && rm -rf /var/lib/apt/lists/*
ENV CINEMA_BROWSER=/usr/bin/chromium-headless-shell
WORKDIR /cinema/frontend
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend ./
WORKDIR /cinema
COPY backend backend
COPY docs docs
COPY pytest.ini .
CMD ["python", "backend/tests/verify.py"]
