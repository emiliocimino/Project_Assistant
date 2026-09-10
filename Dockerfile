FROM node:22-bookworm-slim
LABEL authors="emiliocimino"

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /uvx /bin/

WORKDIR /home
COPY . .

RUN uv sync --project pyproject.toml

ENTRYPOINT ["uv", "run", "python", "-m", "src.app"]