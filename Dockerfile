FROM node:22-bookworm-slim
LABEL authors="emiliocimino"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /home
COPY . .
RUN mkdir src/data
RUN mkdir src/data/sources
RUN mkdir src/data/wiki


RUN uv sync --project pyproject.toml

ENTRYPOINT ["uv", "run", "python", "-m", "src.app"]