#!/bin/sh

# Configuration - Update these or use environment variables
IMAGE_NAME="raiven-mcp"
NEO4J_PASS_FILE="${RAIVEN_NEO4J_PASSWORD_FILE:-~/.config/sops-nix/secrets/server1os1-neo4j-password}"
OLLAMA_KEY_FILE="${RAIVEN_OLLAMA_API_KEY_FILE:-~/.config/sops-nix/secrets/server1os1-ollama-api-key}"

# Helper to read secrets
read_secret() {
    local file=$1
    if [[ -f "$file" ]]; then
        cat "$file" | tr -d '\n' | tr -d '\r'
    else
        echo ""
    fi
}

echo "Reading secrets..."
NEO4J_PASSWORD=$(read_secret "$NEO4J_PASS_FILE")
OLLAMA_API_KEY=$(read_secret "$OLLAMA_KEY_FILE")

if [[ -z "$NEO4J_PASSWORD" ]]; then
    echo "Warning: Neo4j password not found in $NEO4J_PASS_FILE"
fi

if [[ -z "$OLLAMA_API_KEY" ]]; then
    echo "Warning: Ollama API key not found in $OLLAMA_KEY_FILE"
fi

echo "Building Docker image: $IMAGE_NAME..."

docker build \
    --build-arg RAIVEN_NEO4J_PASSWORD="$NEO4J_PASSWORD" \
    --build-arg RAIVEN_OLLAMA_API_KEY="$OLLAMA_API_KEY" \
    -t "$IMAGE_NAME" .

echo "Build complete."
