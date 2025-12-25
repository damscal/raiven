Here is the comprehensive technical documentation for the **Holographic Cognitive Memory System (HCMS)**.

---

# RAIVEN: Holographic Cognitive Memory System (HCMS)
### Architecture & Implementation Guide

**Version:** 2.0.0
**Date:** December 25, 2025
**Backend:** Neo4j 5.x + Python 3.11+
**Architecture:** Dual-Process (Active Consciousness + Subconscious Metabolism)

---

## 1. System Overview

The **HCMS** is a hybrid memory architecture designed to provide Large Language Models (LLMs) with long-term, structured, and abstractive memory. 

### Core Philosophy: The Dual-Process Architecture
1.  **Active Consciousness (MCP Server):** The fast interface for immediate interaction. Handles text storage, graph updates (mentions), and holographic retrieval. It is optimized for zero-latency in conversations.
2.  **Subconscious Metabolism (Background Worker):** The slow, reflective process. It handles heavy compute tasks:
    *   **Delayed Embedding:** Generates vector embeddings for new chunks at a controlled pace.
    *   **Cognitive Dissonance Detection:** Uses advanced LLMs to identify contradictions between new and existing knowledge.
    *   **RAPTOR Consolidation:** Builds the recursive summarization tree.

---

## 2. Memory Layers

1.  **Episodic Memory (The Stream):** Stores raw interactions as vector-embedded chunks.
2.  **Semantic Memory (The Web):** Heuristically extracts entities and builds a knowledge graph. Supports client-side entity extraction to save resources.
3.  **Abstractive Memory (The Tree):** Uses **RAPTOR** to group chunks and generate higher-level summaries via internal LLM.

---

## 3. Cognitive Mechanisms

### A. Delayed Processing
To maintain stability on limited hardware, all Ollama-based operations (embeddings, chat generation for summaries) are deferred to the metabolism phase. Chunks are stored with a `needs_embedding: true` flag.

### B. Cognitive Dissonance
The Subconscious Metabolism periodically reviews unchecked memories:
*   **Verification:** Compares new info against retrieved context using a capable model (`SUBCONSCIOUS_MODEL`).
*   **Flagging:** If a conflict is detected, the memory is marked with `potential_dissonance: true` and a report is generated.
*   **Resolution:** Malik (the active consciousness) is notified during chat and can resolve the issue using `resolve_dissonance` or `update_memory_chunk`.

### C. Synaptic Pruning
Raiven mimics biological brains by pruning "weak" connections. Relationships in the knowledge graph have a `weight` property that decays or strengthens based on reinforcement.

---

## 4. MCP Integration

Raiven exposes its capabilities through the **Model Context Protocol (MCP)**.

### Primary Tools:
*   **`add_memory(text, entities)`**: Immediate ingestion. Accepting client-side entities for optimization.
*   **`retrieve_memory(query)`**: Holographic recall (Hybrid search).
*   **`query_knowledge_graph(cypher)`**: Direct Cypher access for high-speed relational queries (Bypasses Ollama).
*   **`chat_with_memory(prompt)`**: Intelligent reasoning over memory with dissonance warnings.
*   **`update_memory_chunk(chunk_id, new_text)`**: Direct memory editing.
*   **`resolve_dissonance(chunk_id, resolution)`**: Human-in-the-loop conflict resolution.
*   **`trigger_consolidation()`**: Forces immediate metabolic processing.

---

## 6. Development

### Project Structure:
*   `src/raiven/`: Core Python package.
*   `src/raiven_mcp.py`: MCP Server implementation.
*   `utils/test_pipeline.py`: End-to-end verification suite.
*   `Dockerfile`: Containerization logic.
