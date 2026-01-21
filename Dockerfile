# Development Dockerfile for Baijerilainen ECU Optimizer
FROM oven/bun:1 AS base

# Install system dependencies and Python
RUN apt-get update && apt-get install -y \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy package files first for better caching
COPY package.json bun.lock* ./
COPY pyproject.toml uv.lock* ./

# Install Node.js dependencies
RUN bun install

# Install Python dependencies with uv
RUN uv sync

# Copy the rest of the application
COPY . .

# Expose the dev server port
EXPOSE 5173

# Run the Svelte dev server with host binding for Docker
CMD ["bun", "run", "dev", "--host", "0.0.0.0"]
