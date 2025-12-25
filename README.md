# RAIVEN: Holographic Cognitive Memory System (HCMS)

RAIVEN is a Nix-flaked Python application that implements a Holographic Cognitive Memory System (HCMS). It provides a GraphRAG + RAPTOR architecture for long-term, structured, and abstractive memory for Large Language Models (LLMs), using Neo4j as the graph-vector database and Ollama for embeddings.

## Features

- **Dual-Process Architecture**: Decouples the fast "Active Consciousness" (MCP interaction) from the slow "Subconscious Metabolism" (background processing).
- **GraphRAG + RAPTOR**: Combines graph-based retrieval with recursive abstractive processing for multi-level memory access.
- **Cognitive Dissonance Detection**: Automatically flags potential contradictions in long-term memory for conscious review.
- **Holographic Retrieval**: Simultaneously queries specific details, abstract summaries, and relational facts.
- **Resource Optimized**: Designed to run effectively on hardware with limited CPU/RAM by spreading compute load over time.
- **Nix Flake & Docker**: Reproducible builds and flexible deployment options (Nix or Docker).

## Prerequisites

- [Docker](https://www.docker.com/) (Recommended for dual-process deployment).
- [Nix](https://nixos.org/download.html) with flakes enabled.
- Access to a Neo4j 5.x+ instance with vector index support.
- Access to an Ollama instance.

## Installation & Usage

### As a Dual-Process Docker System (Recommended)

1. Build the image:
   ```bash
   ./rebuild.sh
   ```

2. Run the **Active Consciousness (MCP Server)**:
   ```bash
   docker run --env-file .env raiven-memory-server
   ```

3. Run the **Subconscious Metabolism**:
   ```bash
   docker run --env-file .env raiven-memory-server python /app/src/raiven_metabolism.py
   ```

### As a Nix Package

To build and run the MCP server directly:
```bash
nix run
```

## Configuration

RAIVEN is configured through environment variables.

### Environment Variables

- `RAIVEN_NEO4J_URI`: Neo4j connection URI.
- `RAIVEN_NEO4J_USER`: Neo4j username.
- `RAIVEN_NEO4J_PASSWORD`: Neo4j password.
- `RAIVEN_OLLAMA_HOST`: Ollama host URI.
- `RAIVEN_OLLAMA_API_KEY`: Ollama API key.
- `RAIVEN_OLLAMA_MODEL`: Ollama embedding model (default: `embeddinggemma:latest`).
- `RAIVEN_OLLAMA_CHAT_MODEL`: Ollama chat model for reasoning (default: `gemma:2b`).
- `RAIVEN_OLLAMA_SUBCONSCIOUS_MODEL`: Ollama model for dissonance analysis (default: `gemma:2b`).
- `RAIVEN_VECTOR_DIMENSIONS`: Vector dimensions (default: 768).

Secret files are read by the application, and paths can contain `~` which will be expanded.

## Project Structure

- `raiven.py`: Core Python application logic.
- `pyproject.toml`: Python package metadata.
- `flake.nix`: Nix flake definition for packaging and development environment.
- `hm-module.nix`: Home Manager module for the systemd service.
- `implementation guide.md`: Technical details of the HCMS architecture.
- `USAGE.md`: Detailed usage instructions.
- `CONTRIBUTING.md`: Guidelines for contributing to the project.
