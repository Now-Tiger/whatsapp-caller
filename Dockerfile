FROM python:3.12-slim-bookworm

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency manifest first (layer cache for deps)
COPY pyproject.toml .

# Copy application source
COPY bot.py .
COPY bot_prompt.py .

# Install production dependencies only
RUN uv sync --frozen --no-dev

CMD ["uv", "run", "bot.py"]
