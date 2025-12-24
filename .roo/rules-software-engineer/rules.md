Project: Raiven - Holographic Cognitive Memory System (HCMS)
Stack: Python, Neo4j, Sentence-Transformers
Graph Schema:
- (:Chunk) -> Episodic
- (:Entity) -> Semantic
- (:Summary) -> RAPTOR (Recursive Abstractive)
Rules:
- All Neo4j queries must use parameters (no f-strings).
- Every time a new function is added, update the 'add_memory' pipeline.
- Maintain the 384-dimension vector consistency.