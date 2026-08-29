FROM astral/uv:python3.12-bookworm-slim
LABEL authors="emiliocimino"

WORKDIR /home
COPY . .
RUN mkdir src/data
RUN mkdir src/data/sources
RUN mkdir src/data/wiki


RUN uv sync --project pyproject.toml

ENTRYPOINT ["uv", "run", "python", "-m", "src.app"]