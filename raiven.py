import os
import uuid
import numpy as np
from typing import List, Dict, Any
from datetime import datetime
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

# --- Configuration ---
# In a real app, load these from .env
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password" 

class CognitiveMemory:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        # Using a lightweight local model for embeddings (384 dimensions)
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self._initialize_schema()

    def close(self):
        self.driver.close()

    def _initialize_schema(self):
        """
        Sets up Vector Indexes and Constraints in Neo4j 5.x+
        """
        with self.driver.session() as session:
            # 1. Vector Index for Raw Episodes (Chunks)
            session.run("""
                CREATE VECTOR INDEX chunk_embeddings IF NOT EXISTS
                FOR (c:Chunk) ON (c.embedding)
                OPTIONS {indexConfig: {
                 `vector.dimensions`: 384,
                 `vector.similarity_function`: 'cosine'
                }}
            """)
            
            # 2. Vector Index for RAPTOR Summaries
            session.run("""
                CREATE VECTOR INDEX summary_embeddings IF NOT EXISTS
                FOR (s:Summary) ON (s.embedding)
                OPTIONS {indexConfig: {
                 `vector.dimensions`: 384,
                 `vector.similarity_function`: 'cosine'
                }}
            """)

            # 3. Constraint for Entities to ensure uniqueness
            session.run("""
                CREATE CONSTRAINT entity_id IF NOT EXISTS 
                FOR (e:Entity) REQUIRE e.name IS UNIQUE
            """)
            print(">> Schema & Indexes Initialized")

    def _embed(self, text: str) -> List[float]:
        return self.encoder.encode(text).tolist()

    # =========================================================
    # PART 1: INGESTION (Episodic + Semantic Extraction)
    # =========================================================
    
    def add_memory(self, text: str, role: str = "user"):
        """
        Ingests interaction, creates a Chunk, and simulates Entity Extraction.
        In production, 'entities' would come from an LLM call.
        """
        embedding = self._embed(text)
        chunk_id = str(uuid.uuid4())
        
        # Simulated LLM Entity Extraction (You would replace this with an LLM call)
        # e.g., "I use Neo4j" -> Extract: "Neo4j"
        extracted_entities = [word for word in text.split() if word[0].isupper()] 

        with self.driver.session() as session:
            session.execute_write(
                self._create_memory_transaction, 
                text, embedding, role, chunk_id, extracted_entities
            )
        
        # Trigger RAPTOR abstraction (Simplified)
        self._update_raptor_tree()

    @staticmethod
    def _create_memory_transaction(tx, text, embedding, role, chunk_id, entities):
        # 1. Create the Episodic Chunk
        query_chunk = """
        CREATE (c:Chunk {
            id: $id, 
            text: $text, 
            role: $role, 
            timestamp: datetime(),
            embedding: $embedding
        })
        """
        tx.run(query_chunk, id=chunk_id, text=text, role=role, embedding=embedding)

        # 2. Link Entities (The Semantic Graph)
        # We merge entities so we don't duplicate "Python" if it exists.
        for entity in entities:
            query_entity = """
            MATCH (c:Chunk {id: $chunk_id})
            MERGE (e:Entity {name: $entity})
            MERGE (c)-[:MENTIONS]->(e)
            """
            tx.run(query_entity, chunk_id=chunk_id, entity=entity)
            
            # 3. (Optional) Auto-connect entities found in same chunk
            # This builds the knowledge graph web implicitly
            query_rel = """
            MATCH (c:Chunk {id: $chunk_id})-[:MENTIONS]->(e1:Entity)
            MATCH (c)-[:MENTIONS]->(e2:Entity)
            WHERE e1 <> e2
            MERGE (e1)-[r:RELATED_TO]->(e2)
            ON CREATE SET r.weight = 1
            ON MATCH SET r.weight = r.weight + 1
            """
            tx.run(query_rel, chunk_id=chunk_id)

    # =========================================================
    # PART 2: RAPTOR (Recursive Summarization)
    # =========================================================

    def _update_raptor_tree(self):
        """
        Simplistic implementation of RAPTOR.
        Groups orphan chunks, summarizes them, and layers them up.
        """
        with self.driver.session() as session:
            # Find recent chunks that are NOT summarized yet
            result = session.run("""
                MATCH (c:Chunk)
                WHERE NOT (c)<-[:SUMMARIZES]-(:Summary)
                RETURN c.text as text, c.id as id
                LIMIT 5 
            """)
            
            chunks = list(result)
            if len(chunks) < 3: return # Wait for more data to summarize

            # Combine text (In real life, LLM generates a summary here)
            combined_text = " ".join([c['text'] for c in chunks])
            summary_text = f"SUMMARY OF {len(chunks)} ITEMS: {combined_text[:50]}..."
            summary_vec = self._embed(summary_text)
            summary_id = str(uuid.uuid4())

            # Write Summary node and link to children
            session.run("""
                CREATE (s:Summary {
                    id: $sid, 
                    text: $stext, 
                    embedding: $svec, 
                    level: 1
                })
                WITH s
                UNWIND $child_ids as cid
                MATCH (c:Chunk {id: cid})
                MERGE (s)-[:SUMMARIZES]->(c)
            """, sid=summary_id, stext=summary_text, svec=summary_vec, child_ids=[c['id'] for c in chunks])
            
            print(f">> RAPTOR: Created Level 1 Summary for {len(chunks)} chunks.")

    # =========================================================
    # PART 3: HOLOGRAPHIC RETRIEVAL
    # =========================================================

    def retrieve(self, query: str, top_k: int = 3):
        query_vec = self._embed(query)
        
        with self.driver.session() as session:
            # Strategy A: Low-level Episodic Search (Vector)
            # Using Neo4j 5.x db.index.vector.queryNodes
            episodic_result = session.run("""
                CALL db.index.vector.queryNodes('chunk_embeddings', $k, $vec)
                YIELD node, score
                RETURN node.text as text, score
            """, k=top_k, vec=query_vec)
            
            # Strategy B: High-level Abstract Search (RAPTOR)
            raptor_result = session.run("""
                CALL db.index.vector.queryNodes('summary_embeddings', 2, $vec)
                YIELD node, score
                RETURN node.text as text, score
            """, vec=query_vec)

            # Strategy C: Graph Traversal (Knowledge Graph)
            # Find entities in query, then find what they are related to
            # (Simple keyword match for demo, use NER in prod)
            keywords = [w for w in query.split() if w[0].isupper()]
            graph_context = []
            
            if keywords:
                res = session.run("""
                    MATCH (e:Entity)
                    WHERE e.name IN $keywords
                    MATCH (e)-[r:RELATED_TO]-(neighbor)
                    RETURN e.name + ' is related to ' + neighbor.name as fact
                    LIMIT 5
                """, keywords=keywords)
                graph_context = [r['fact'] for r in res]

            return {
                "episodic_hits": [r['text'] for r in episodic_result],
                "raptor_summary": [r['text'] for r in raptor_result],
                "knowledge_graph": graph_context
            }

# --- USAGE DEMO ---
if __name__ == "__main__":
    brain = CognitiveMemory()
    
    # 1. Feed it data (Episodic Stream)
    print("--- Ingesting Memories ---")
    brain.add_memory("I am working on a Project called Omega.")
    brain.add_memory("Omega uses Python and Neo4j for the backend.")
    brain.add_memory("I prefer using FastAPI over Flask.")
    brain.add_memory("The database must be self-hosted.")
    
    # 2. Query (The Holographic Retrieval)
    print("\n--- Retrieving Context ---")
    query = "What is the tech stack for Omega?"
    context = brain.retrieve(query)
    
    print(f"Query: {query}\n")
    print(f"RAPTOR (High Level): {context['raptor_summary']}")
    print(f"GRAPH (Facts): {context['knowledge_graph']}")
    print(f"EPISODIC (Details): {context['episodic_hits']}")
    
    brain.close()