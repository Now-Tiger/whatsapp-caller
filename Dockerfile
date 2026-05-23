# ---------- Stage 1: Build (Heavy Lifting) ----------
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

# Force uv to compile bytecode for speed and immutability
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy blueprints
COPY pyproject.toml uv.lock ./

# Sync dependencies into a standalone virtual environment
RUN uv sync --frozen --no-install-project

# ---------- Stage 2: Secure, Lightweight Pure-UV Runtime ----------
FROM python:3.13-slim AS final

# Standard Python optimizations
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Tell uv to look inside the local .venv directory and skip creating its own cache system
ENV UV_PROJECT_ENVIRONMENT="/app/.venv"
ENV UV_NO_CACHE=1

WORKDIR /app

# 1. CRITICAL SECURITY FEATURE: Copy the uv binary directly from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvbin/uv
ENV PATH="/uvbin:$PATH"

# 2. CRITICAL SIZE FEATURE: Copy ONLY the compiled production environment (No /root/.cache bloat)
COPY --from=builder /app/.venv /app/.venv

# Copy application files
COPY bot.py bot_prompt.py ./

# Create a secure, non-root system user with an explicit home directory
RUN groupadd -r botuser && useradd -r -m -g botuser botuser
RUN chown -R botuser:botuser /app

USER botuser

EXPOSE 7860

# Production health check utilizing uv wrapper for security consistency
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD uv run python -c "import sys; sys.exit(0)" || exit 1

# Run the bot strictly using the uv runtime engine
CMD ["uv", "run", "bot.py"]
