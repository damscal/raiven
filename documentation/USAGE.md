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
You can segregate memories by user or project using different Neo4j databases.

```python
project_a_memory = CognitiveMemory(database="projectA")
project_b_memory = CognitiveMemory(database="projectB")
```

### Clearing Memory (Testing)
To clear a test database:

```python
brain = CognitiveMemory(database="testdb")
brain._query_neo4j("MATCH (n) DETACH DELETE n")
```

## System Maintenance

The **RAPTOR** process (summarization) triggers automatically every 5 chunks by default. For high-volume ingestion, it is recommended to monitor the `:Summary` node creation in the Neo4j Browser:

```cypher
MATCH (s:Summary)-[:SUMMARIZES]->(c:Chunk)
RETURN s, c
```
