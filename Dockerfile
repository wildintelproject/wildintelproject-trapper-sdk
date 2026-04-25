FROM python:3.10-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install dependencies first (efficient layer cache)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy source and install the project
COPY src ./src
RUN uv sync --frozen --no-dev

CMD ["python"]
