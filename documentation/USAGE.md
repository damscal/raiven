# RAIVEN Usage Guide

This document provides detailed instructions on how to use the RAIVEN Holographic Cognitive Memory System.

## Overview

RAIVEN operates as a background service when deployed via Home Manager. It continuously ingests memories and makes them available for holographic retrieval. The system can also be run directly for testing or development purposes.

## Running RAIVEN

### As a Home Manager Service (Recommended)

When configured as a Home Manager service, RAIVEN will start automatically and run in the background. The service is managed by systemd.

1. Ensure your Home Manager configuration includes the `services.raiven` block with all necessary settings.
2. Run `home-manager switch` to apply the configuration.
3. The service will be started. You can check its status with:
   ```bash
   systemctl --user status raiven
   ```
4. To view logs:
   ```bash
   journalctl --user -u raiven -f
   ```

### Direct Execution (Development/Testing)

To run RAIVEN directly (e.g., for testing), you need to set the required environment variables.

Example:

```bash
export RAIVEN_NEO4J_URI="https://your-neo4j-instance.com/"
export RAIVEN_NEO4J_USER="neo4j"
export RAIVEN_NEO4J_PASSWORD_FILE="~/.config/sops-nix/secrets/neo4j_password"
export RAIVEN_OLLAMA_HOST="https://your-ollama-instance.com/"
export RAIVEN_OLLAMA_API_KEY_FILE="~/.config/sops-nix/secrets/ollama_api_key"
export RAIVEN_VECTOR_DIMENSIONS=768

python raiven.py
```

## Interacting with RAIVEN

RAIVEN currently ingests memories via the `add_memory` function and retrieves them via the `retrieve` function. In the current implementation, this happens within the `main` function when the script is run, demonstrating the core functionality.

For a persistent, interactive system, you would typically build an API layer (e.g., using FastAPI) that calls these functions. The core logic is encapsulated in the `CognitiveMemory` class.

### Example Interaction Flow

1. **Ingestion**: Call `cognitive_memory.add_memory("Your text here", role="user")`. This:
   - Creates a `:Chunk` node with the text and its embedding.
   - Extracts entities and creates `:Entity` nodes, linking them to the Chunk.
   - Triggers the RAPTOR process to potentially create a `:Summary`.

2. **Retrieval**: Call `cognitive_memory.retrieve("Your query here", top_k=3)`. This:
   - Performs vector similarity search on `:Chunk` nodes (Episodic).
   - Performs vector similarity search on `:Summary` nodes (RAPTOR).
   - Performs graph traversal based on entities in the query (Knowledge Graph).
   - Returns a dictionary with results from all three strategies.

## Configuration Details

### Vector Dimensions

It is crucial that the `RAIVEN_VECTOR_DIMENSIONS` (or the `vectorDimensions` option in Home Manager) matches the output dimension of the embedding model specified by `RAIVEN_OLLAMA_MODEL`. The system defaults to 768, which is common for models like `embeddinggemma:latest`.

### Neo4j Authentication

RAIVEN supports two methods for Neo4j authentication:
- **Basic Auth**: Provide `RAIVEN_NEO4J_USER` and `RAIVEN_NEO4J_PASSWORD_FILE`.
- **API Key Auth**: Provide `RAIVEN_NEO4J_API_KEY_FILE`. If an API key is provided, it takes precedence over basic auth.

### Ollama Integration

RAIVEN uses Ollama for generating embeddings. Ensure the specified `RAIVEN_OLLAMA_MODEL` is available on your Ollama instance. The `RAIVEN_OLLAMA_API_KEY_FILE` is optional and depends on your Ollama setup.

## Troubleshooting

- **Connection Issues**: Verify that the Neo4j and Ollama URIs are accessible and that the credentials/api keys are correct.
- **Embedding Errors**: Ensure the Ollama model is loaded and responding. Check that the vector dimensions match.
- **Service Not Starting**: Check `journalctl --user -u raiven -f` for error messages from the systemd service.
- **Secrets Not Found**: Ensure the paths to secret files are correct and the files are readable by the user running the service.
