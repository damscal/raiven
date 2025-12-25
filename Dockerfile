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

# ARG for the password, to be passed with $(cat ...)
ARG RAIVEN_NEO4J_PASSWORD
ENV RAIVEN_NEO4J_PASSWORD=${RAIVEN_NEO4J_PASSWORD}

# ARG for Ollama API Key
ARG RAIVEN_OLLAMA_API_KEY
ENV RAIVEN_OLLAMA_API_KEY=${RAIVEN_OLLAMA_API_KEY}

# By default run the MCP server, but allow overriding to run metabolism
ENTRYPOINT ["python"]
CMD ["/app/src/raiven_mcp.py"]
