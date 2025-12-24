# Use a lightweight Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements or project files
COPY pyproject.toml .
COPY src/ ./src/

# Install the package and its dependencies
RUN pip install --no-cache-dir .

# Force logs to be unbuffered
ENV PYTHONUNBUFFERED=1

# Run the MCP server
# Use direct script call to avoid any potential -m issues with packages
ENTRYPOINT ["python", "/app/src/raiven_mcp.py"]
