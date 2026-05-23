# ---------- Stage 1: Build & Verify ----------
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-install-project

# ---------- Stage 2: Secure Runtime ----------
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS final

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

ENV UV_CACHE_DIR="/app/.uv_cache"

WORKDIR /app

# Create system user AND explicitly create a matching home directory
RUN groupadd -r botuser && useradd -r -m -g botuser botuser

COPY --from=builder /root/.cache /root/.cache
COPY --from=builder /app /app

COPY bot.py bot_prompt.py ./

# Ensure the entire app folder (including the new cache target) belongs to botuser
RUN chown -R botuser:botuser /app

USER botuser

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD uv run python -c "import sys; sys.exit(0)" || exit 1

CMD ["uv", "run", "bot.py"]
