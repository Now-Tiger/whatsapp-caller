# ---------- Stage 1: Build ----------
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

# Optimized UV configuration
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
# Install dependencies into a standard location for easy copying
ENV UV_PROJECT_ENVIRONMENT="/venv"

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies with uv
RUN uv sync --frozen

# Stage 2: Runtime image
FROM python:3.13-slim AS final

# Standard Python optimizations
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application files
COPY bot.py bot_prompt.py ./

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/opt/venv/lib/python3.12/site-packages"

# Expose port (if needed for local development)
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run the bot
CMD ["uv", "run", "bot.py"]
