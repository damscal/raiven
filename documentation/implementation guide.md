Here is the comprehensive technical documentation for the **Holographic Cognitive Memory System (HCMS)**.

---

# RAIVEN: Holographic Cognitive Memory System (HCMS)
### Architecture & Implementation Guide

**Version:** 1.2.0
**Date:** December 2025
**Backend:** Neo4j 5.x + Python 3.11+
**Deployment:** Docker / Nix

---

## 1. System Overview

The **HCMS** is a hybrid memory architecture designed to provide Large Language Models (LLMs) with long-term, structured, and abstractive memory. 

### Core Philosophy
1.  **Episodic Memory (The Stream):** Stores raw interactions as vector-embedded chunks.
2.  **Semantic Memory (The Web):** Heuristically extracts entities and builds a knowledge graph.
3.  **Abstractive Memory (The Tree):** Uses **RAPTOR** to group chunks and generate higher-level summaries.

---

## 2. Deployment

Raiven can be deployed as a local Python package, a Nix-based troubleshooting environment, or a device-agnostic Docker container.

### A. Docker (Recommended for MCP)
The system includes a `Dockerfile` that packages the core library and the MCP server.

```bash
docker build -t raiven-mcp .
```

### B. Nix
For NixOS users, the `flake.nix` and `shell.nix` provide a fully reproducible environment.

```bash
nix-shell
```

---

## 3. Configuration

Configured via environment variables.

| Variable | Description | Default |
|----------|-------------|---------|
| `RAIVEN_NEO4J_URI` | Neo4j REST API endpoint | `https://server1os1.oneira.pp.ua/neo4j/` |
| `RAIVEN_NEO4J_DATABASE` | Database name | `neo4j` |
| `RAIVEN_OLLAMA_HOST` | Ollama API endpoint | `https://server1os1.oneira.pp.ua/ollama/` |
| `RAIVEN_OLLAMA_MODEL` | Embedding model | `embeddinggemma:latest` |

---

## 4. MCP Integration

Raiven exposes its capabilities through the **Model Context Protocol (MCP)**, allowing AI agents like Roo Code to use it as a native tool.

### Exposed Tools:
*   **`add_memory(text: str)`**: Ingests new information.
*   **`retrieve_memory(query: str)`**: Recalls holographic context (Vector + Graph + RAPTOR).

---

## 5. Development

### Project Structure:
*   `src/raiven/`: Core Python package.
*   `src/raiven_mcp.py`: MCP Server implementation.
*   `utils/test_pipeline.py`: End-to-end verification suite.
*   `Dockerfile`: Containerization logic.
