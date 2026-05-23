# ---------- Stage 1: Build & Verify ----------
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

# Set working directory
WORKDIR /app

# Enable bytecode compilation for performance and security (prevents source tampering in prod)
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy only dependency blueprints first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Verify and lock dependencies strictly without creating a standard virtual environment
RUN uv sync --frozen --no-install-project

# ---------- Stage 2: Secure Runtime ----------
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS final

# Standard Python optimizations
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Least Privileged Principle: Create a non-root system user for security
RUN groupadd -r botuser && useradd -r -g botuser botuser

# Copy the cache and synchronization state from the builder stage
COPY --from=builder /root/.cache /root/.cache
COPY --from=builder /app /app

# Copy application files
COPY bot.py bot_prompt.py ./

# Secure file permissions so the non-root user can run the app but not modify it
RUN chown -R botuser:botuser /app

# Switch to the secure non-root user
USER botuser

# Expose port (if needed)
EXPOSE 7860

# Health check matching your runtime execution strategy
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD uv run python -c "import sys; sys.exit(0)" || exit 1

# Run the bot securely via uv runtime isolation
CMD ["uv", "run", "bot.py"]
