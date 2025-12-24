import os
import uuid
import json
import requests
import numpy as np
from typing import List, Dict, Any
from datetime import datetime
from neo4j import GraphDatabase

# --- Configuration Loader ---
def get_config(key: str, default: Any = None) -> Any:
    return os.getenv(key, default)

def read_secret(file_path: str) -> str:
    if not file_path:
        return ""
    full_path = os.path.expanduser(file_path)
    if os.path.isfile(full_path):
        try:
            with open(full_path, "r") as f:
                return f.read().strip()
        except Exception as e:
            print(f"Warning: Could not read secret file at {full_path}: {e}")
    return ""

# Configuration from environment variables (set by Home Manager service)
NEO4J_URI = get_config("RAIVEN_NEO4J_URI", "https://server1os1.oneira.pp.ua/neo4j/")
NEO4J_USER = get_config("RAIVEN_NEO4J_USER", "neo4j")
NEO4J_PASSWORD = read_secret(get_config("RAIVEN_NEO4J_PASSWORD_FILE"))
NEO4J_API_KEY = read_secret(get_config("RAIVEN_NEO4J_API_KEY_FILE"))

OLLAMA_HOST = get_config("RAIVEN_OLLAMA_HOST", "https://server1os1.oneira.pp.ua/ollama/")
OLLAMA_API_KEY = read_secret(get_config("RAIVEN_OLLAMA_API_KEY_FILE"))
EMBEDDING_MODEL = get_config("RAIVEN_OLLAMA_MODEL", "embeddinggemma:latest")
VECTOR_DIMENSIONS = int(get_config("RAIVEN_VECTOR_DIMENSIONS", "768"))

class CognitiveMemory:
    def __init__(self):
        # Neo4j 5.x connection
        if NEO4J_API_KEY:
            from neo4j import Auth
            auth = Auth.api_key(NEO4J_API_KEY)
        else:
            auth = (NEO4J_USER, NEO4J_PASSWORD)

        self.driver = GraphDatabase.driver(NEO4J_URI, auth=auth)
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
                 `vector.dimensions`: $dims,
                 `vector.similarity_function`: 'cosine'
                }}
            """, dims=VECTOR_DIMENSIONS)
            
            # 2. Vector Index for RAPTOR Summaries
            session.run("""
                CREATE VECTOR INDEX summary_embeddings IF NOT EXISTS
                FOR (s:Summary) ON (s.embedding)
                OPTIONS {indexConfig: {
                 `vector.dimensions`: $dims,
                 `vector.similarity_function`: 'cosine'
                }}
            """, dims=VECTOR_DIMENSIONS)

            # 3. Constraint for Entities to ensure uniqueness
            session.run("""
                CREATE CONSTRAINT entity_id IF NOT EXISTS 
                FOR (e:Entity) REQUIRE e.name IS UNIQUE
            """)
            print(f">> Schema & Indexes Initialized (Dimensions: {VECTOR_DIMENSIONS})")

    def _embed(self, text: str) -> List[float]:
        """
        Calls Ollama API for embeddings.
        """
        url = f"{OLLAMA_HOST.rstrip('/')}/api/embeddings"
        headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}"} if OLLAMA_API_KEY else {}
        payload = {
            "model": EMBEDDING_MODEL,
            "prompt": text
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()["embedding"]
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            raise

    # =========================================================
    # PART 1: INGESTION (Episodic + Semantic Extraction)
    # =========================================================
    
    def add_memory(self, text: str, role: str = "user"):
        embedding = self._embed(text)
        chunk_id = str(uuid.uuid4())
        extracted_entities = [word.strip(".,!?") for word in text.split() if word[0].isupper() and len(word) > 1] 

        with self.driver.session() as session:
            session.execute_write(
                self._create_memory_transaction, 
                text, embedding, role, chunk_id, extracted_entities
            )
        self._update_raptor_tree()

    @staticmethod
    def _create_memory_transaction(tx, text, embedding, role, chunk_id, entities):
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

        for entity in entities:
            query_entity = """
            MATCH (c:Chunk {id: $chunk_id})
            MERGE (e:Entity {name: $entity})
            MERGE (c)-[:MENTIONS]->(e)
            """
            tx.run(query_entity, chunk_id=chunk_id, entity=entity)
            
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
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Chunk)
                WHERE NOT (c)<-[:SUMMARIZES]-(:Summary)
                RETURN c.text as text, c.id as id
                LIMIT 5 
            """)
            
            chunks = list(result)
            if len(chunks) < 3: return

            combined_text = " ".join([c['text'] for c in chunks])
            summary_text = f"Composite Memory: {combined_text[:100]}..."
            summary_vec = self._embed(summary_text)
            summary_id = str(uuid.uuid4())

            session.run("""
                CREATE (s:Summary {
                    id: $sid, 
                    text: $stext, 
                    embedding: $svec, 
                    level: 1,
                    timestamp: datetime()
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
            episodic_result = session.run("""
                CALL db.index.vector.queryNodes('chunk_embeddings', $k, $vec)
                YIELD node, score
                RETURN node.text as text, score
            """, k=top_k, vec=query_vec)
            
            raptor_result = session.run("""
                CALL db.index.vector.queryNodes('summary_embeddings', 2, $vec)
                YIELD node, score
                RETURN node.text as text, score
            """, vec=query_vec)

            keywords = [w.strip(".,!?") for w in query.split() if w[0].isupper() and len(w) > 1]
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

def main():
    brain = CognitiveMemory()
    try:
        print("--- RAIVEN HCMS ACTIVE ---")
        print("--- Ingesting Memories ---")
        brain.add_memory("I am working on a Project called Omega.")
        brain.add_memory("Omega uses Python and Neo4j for the backend.")
        
        print("\n--- Retrieving Context ---")
        query = "What is the tech stack for Omega?"
        context = brain.retrieve(query)
        print(f"Query: {query}")
        print(f"Facts: {context['knowledge_graph']}")
    finally:
        brain.close()

if __name__ == "__main__":
    main()
