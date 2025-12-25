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
| `RAIVEN_NEO4J_DATABASE` | Database name (Fixed to `neo4j` in Community Edition) | `neo4j` |
| `RAIVEN_OLLAMA_HOST` | Ollama API endpoint | `https://server1os1.oneira.pp.ua/ollama/` |
| `RAIVEN_OLLAMA_MODEL` | Embedding model | `embeddinggemma:latest` |

---

## 4. MCP Integration

Raiven exposes its capabilities through the **Model Context Protocol (MCP)**, allowing AI agents like Roo Code to use it as a native tool.

### Exposed Tools:
*   **`add_memory(text: str)`**: Ingests new information. Triggers automatic synaptic pruning and cognitive dissonance decay.
*   **`retrieve_memory(query: str)`**: Recalls holographic context (Vector + Graph + RAPTOR).
*   **`forget_memory(chunk_id: str)`**: Removes a specific memory chunk and prunes orphaned graph nodes.

---

## 5. Cognitive Mechanisms

### A. Synaptic Pruning
Raiven mimics biological brains by pruning "weak" connections. Relationships in the knowledge graph have a `weight` property. If a relationship's weight falls below `0.5`, it is automatically deleted during the next ingestion cycle.

### B. Competitive Plasticity (Cognitive Dissonance)
When new information about an entity is received, Raiven applies a small decay (`-0.5`) to all existing relationships for that entity.
*   **Reinforcement:** If the new info matches existing patterns, the weight is increased (+1.0), overcoming the decay.
*   **Contradiction/Neglect:** If the info is not reinforced, the connections continue to weaken until they are pruned.

---

## 6. Development

### Project Structure:
*   `src/raiven/`: Core Python package.
*   `src/raiven_mcp.py`: MCP Server implementation.
*   `utils/test_pipeline.py`: End-to-end verification suite.
*   `Dockerfile`: Containerization logic.
