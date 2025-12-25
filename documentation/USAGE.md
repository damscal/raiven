# Raiven Usage Guide

This guide covers basic operations for the Holographic Cognitive Memory System.

## Quick Start

1.  **Environment Setup**:
    Ensure your Neo4j and Ollama environment variables are set. See `documentation/implementation guide.md` for details.

2.  **Basic Interaction**:

```python
from raiven import CognitiveMemory

# Initialize
brain = CognitiveMemory()

# 1. Add Memory
brain.add_memory("The server is located in the London data center.")
brain.add_memory("It runs on a NixOS configuration with 64GB RAM.")

# 2. Retrieve Context
context = brain.retrieve("Tell me about the server infrastructure.")

# 3. Use in your LLM Prompt
prompt = f"""
Answer the user query using the following context:
EPISODIC: {context['episodic_hits']}
SUMMARY: {context['raptor_summary']}
FACTS: {context['knowledge_graph']}

User: Tell me about the server.
"""
```

## Advanced Operations

### Targeting Different Databases
**Note:** In Neo4j Community Edition, only one database (`neo4j`) is supported. Multi-database segregation is an Enterprise feature and is currently disabled in Raiven.

### Clearing Memory (Testing)
To clear the memory in the default database:

```python
from raiven import CognitiveMemory
brain = CognitiveMemory()
brain._query_neo4j("MATCH (n) DETACH DELETE n")
```

## System Maintenance

The system uses a **Subconscious Metabolism** process (`raiven-metabolism`) to handle background tasks:
1.  **Embedding Generation**: Converts text chunks into vector embeddings.
2.  **Cognitive Dissonance Analysis**: Flags potential contradictions between new and existing memories.
3.  **RAPTOR Summarization**: Automatically consolidates recent memories into higher-level abstract summaries.

### Running the Metabolism
In the production environment, the metabolism is managed as a **NixOS Systemd Service**.

*   **Check Status**: `systemctl status raiven-metabolism`
*   **Restart Service**: `systemctl restart raiven-metabolism`
*   **Monitor Logs**: `journalctl -u raiven-metabolism -f`

**Note:** The metabolism is intentionally slow to preserve CPU/GPU resources for the active session. If you ingest a large amount of data, it may take several minutes to see updates in the RAPTOR tree.
