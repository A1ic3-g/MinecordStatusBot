FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy project files
COPY pyproject.toml uv.lock .

# Install dependencies
RUN uv sync --no-dev --no-install-project

# Copy the rest of the application
COPY . .

# Ensure data directory exists
RUN mkdir -p data

# Run the application
CMD ["uv", "run", "bot.py"]
