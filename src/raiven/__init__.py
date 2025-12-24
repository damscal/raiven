import os
import uuid
import json
import requests
import base64
import numpy as np
from typing import List, Dict, Any
from datetime import datetime

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
            import sys
            print(f"Warning: Could not read secret file at {full_path}: {e}", file=sys.stderr)
    return ""

# Configuration from environment variables
NEO4J_URI = get_config("RAIVEN_NEO4J_URI", "https://server1os1.oneira.pp.ua/neo4j/")
NEO4J_USER = get_config("RAIVEN_NEO4J_USER", "neo4j")
NEO4J_PASSWORD = read_secret(get_config("RAIVEN_NEO4J_PASSWORD_FILE"))
NEO4J_DATABASE = get_config("RAIVEN_NEO4J_DATABASE") # Default to None to use system default if not set

OLLAMA_HOST = get_config("RAIVEN_OLLAMA_HOST", "https://server1os1.oneira.pp.ua/ollama/")
OLLAMA_API_KEY = read_secret(get_config("RAIVEN_OLLAMA_API_KEY_FILE"))
EMBEDDING_MODEL = get_config("RAIVEN_OLLAMA_MODEL", "embeddinggemma:latest")
VECTOR_DIMENSIONS = int(get_config("RAIVEN_VECTOR_DIMENSIONS", "768"))

class CognitiveMemory:
    def __init__(self, database: str = None):
        self.database = database or NEO4J_DATABASE or "neo4j"
        # We explicitly target the /db/ sub-path under /neo4j/
        self.neo4j_url = f"{NEO4J_URI.rstrip('/')}/db/{self.database}/tx/commit"
            
        self.neo4j_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Database Auth via Basic Auth
        if NEO4J_USER and NEO4J_PASSWORD:
            auth_str = f"{NEO4J_USER}:{NEO4J_PASSWORD}"
            encoded_auth = base64.b64encode(auth_str.encode()).decode()
            self.neo4j_headers["Authorization"] = f"Basic {encoded_auth}"
            
        self._initialize_schema()

    def close(self):
        pass

    def _query_neo4j(self, cypher: str, parameters: Dict[str, Any] = None, database: str = None) -> Dict[str, Any]:
        """
        Executes a Cypher query via the Neo4j REST API.
        """
        # If a specific database is requested for this query, adjust the URL
        url = self.neo4j_url
        if database:
            url = f"{NEO4J_URI.rstrip('/')}/db/{database}/tx/commit"

        payload = {
            "statements": [
                {
                    "statement": cypher,
                    "parameters": parameters or {}
                }
            ]
        }
        response = requests.post(url, json=payload, headers=self.neo4j_headers)
        response.raise_for_status()
        
        data = response.json()
        if data.get("errors"):
            raise Exception(f"Neo4j Error: {data['errors']}")
        return data

    def list_databases(self) -> List[str]:
        """
        Lists all available databases in the Neo4j instance.
        Note: SHOW DATABASES requires administrative privileges and usually 
        runs against the 'system' database.
        """
        try:
            # We try to query the system database for the list of databases
            res = self._query_neo4j("SHOW DATABASES", database="system")
            # results[0].data -> list of {row: [name, ...]}
            rows = res["results"][0]["data"]
            return [r["row"][0] for r in rows if r["row"][0] != "system"]
        except Exception as e:
            print(f"Warning: Could not list databases: {e}")
            return [self.database]

    def switch_database(self, database_name: str):
        """
        Switches the active database profile.
        """
        self.database = database_name
        self.neo4j_url = f"{NEO4J_URI.rstrip('/')}/db/{self.database}/tx/commit"
        self._initialize_schema()
        import sys
        print(f">> Switched to database profile: {self.database}", file=sys.stderr)

    def create_database(self, database_name: str):
        """
        Creates a new database in Neo4j.
        """
        self._query_neo4j(f"CREATE DATABASE {database_name} IF NOT EXISTS", database="system")
        import sys
        print(f">> Created database: {database_name}", file=sys.stderr)

    def drop_database(self, database_name: str):
        """
        Removes a database from Neo4j.
        """
        self._query_neo4j(f"DROP DATABASE {database_name} IF EXISTS", database="system")
        import sys
        print(f">> Dropped database: {database_name}", file=sys.stderr)

    def _initialize_schema(self):
        # We use a try-except block and print to stderr to avoid polluting stdout for MCP
        try:
            # First, check if database exists and is online
            try:
                self._query_neo4j("RETURN 1")
            except Exception as e:
                import sys
                print(f"Warning: Database '{self.database}' not ready or accessible: {e}", file=sys.stderr)
                return

            self._query_neo4j(f"""
                CREATE VECTOR INDEX chunk_embeddings IF NOT EXISTS
                FOR (c:Chunk) ON (c.embedding)
                OPTIONS {{indexConfig: {{
                 `vector.dimensions`: {VECTOR_DIMENSIONS},
                 `vector.similarity_function`: 'cosine'
                }}}}
            """)
            
            self._query_neo4j(f"""
                CREATE VECTOR INDEX summary_embeddings IF NOT EXISTS
                FOR (s:Summary) ON (s.embedding)
                OPTIONS {{indexConfig: {{
                 `vector.dimensions`: {VECTOR_DIMENSIONS},
                 `vector.similarity_function`: 'cosine'
                }}}}
            """)

            self._query_neo4j("""
                CREATE CONSTRAINT entity_id IF NOT EXISTS 
                FOR (e:Entity) REQUIRE e.name IS UNIQUE
            """)
            import sys
            print(f">> Schema & Indexes Initialized (Dimensions: {VECTOR_DIMENSIONS}) for database: {self.database}", file=sys.stderr)
        except Exception as e:
            import sys
            print(f"Error initializing schema: {e}", file=sys.stderr)

    def _embed(self, text: str) -> List[float]:
        url = f"{OLLAMA_HOST.rstrip('/')}/api/embeddings"
        headers = {"X-Api-Key": OLLAMA_API_KEY} if OLLAMA_API_KEY else {}
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

    def add_memory(self, text: str, role: str = "user"):
        embedding = self._embed(text)
        chunk_id = str(uuid.uuid4())
        
        # Simple heuristic extraction since Ollama is only for embeddings
        extracted_entities = [word.strip(".,!?") for word in text.split() if word[0].isupper() and len(word) > 1] 

        query_chunk = """
        CREATE (c:Chunk {
            id: $id, 
            text: $text, 
            role: $role, 
            timestamp: datetime(),
            embedding: $embedding
        })
        """
        self._query_neo4j(query_chunk, {"id": chunk_id, "text": text, "role": role, "embedding": embedding})

        for entity_name in extracted_entities:
            query_entity = """
            MATCH (c:Chunk {id: $chunk_id})
            MERGE (e:Entity {name: $entity})
            MERGE (c)-[:MENTIONS]->(e)
            """
            self._query_neo4j(query_entity, {"chunk_id": chunk_id, "entity": entity_name})
            
            query_rel = """
            MATCH (c:Chunk {id: $chunk_id})-[:MENTIONS]->(e1:Entity)
            MATCH (c)-[:MENTIONS]->(e2:Entity)
            WHERE e1 <> e2
            MERGE (e1)-[r:RELATED_TO]->(e2)
            ON CREATE SET r.weight = 1
            ON MATCH SET r.weight = r.weight + 1
            """
            self._query_neo4j(query_rel, {"chunk_id": chunk_id})

        self._update_raptor_tree()

    def _update_raptor_tree(self):
        result = self._query_neo4j("""
            MATCH (c:Chunk)
            WHERE NOT (c)<-[:SUMMARIZES]-(:Summary)
            RETURN c.text as text, c.id as id
            LIMIT 5 
        """)
        
        rows = result["results"][0]["data"]
        chunks = [{"text": r["row"][0], "id": r["row"][1]} for r in rows]
        
        if len(chunks) < 3: return

        # Simple concatenation summary since we don't have a generator LLM in Ollama
        combined_text = " ".join([c['text'] for c in chunks])
        summary_text = f"Summary: {combined_text[:200]}..."
        summary_vec = self._embed(summary_text)
        summary_id = str(uuid.uuid4())

        self._query_neo4j("""
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
        """, {"sid": summary_id, "stext": summary_text, "svec": summary_vec, "child_ids": [c['id'] for c in chunks]})
        import sys
        print(f">> RAPTOR: Created Level 1 Summary for {len(chunks)} chunks.", file=sys.stderr)

    def retrieve(self, query: str, top_k: int = 3):
        query_vec = self._embed(query)
        
        episodic_res = self._query_neo4j("""
            CALL db.index.vector.queryNodes('chunk_embeddings', $k, $vec)
            YIELD node, score
            RETURN node.text as text, score
        """, {"k": top_k, "vec": query_vec})
        
        raptor_res = self._query_neo4j("""
            CALL db.index.vector.queryNodes('summary_embeddings', 2, $vec)
            YIELD node, score
            RETURN node.text as text, score
        """, {"vec": query_vec})

        keywords = [w.strip(".,!?") for w in query.split() if w[0].isupper() and len(w) > 1]
        graph_context = []
        if keywords:
            res = self._query_neo4j("""
                MATCH (e:Entity)
                WHERE e.name IN $keywords
                MATCH (e)-[r:RELATED_TO]-(neighbor)
                RETURN e.name + ' is related to ' + neighbor.name as fact
                LIMIT 5
            """, {"keywords": keywords})
            graph_context = [r["row"][0] for r in res["results"][0]["data"]]

        return {
            "episodic_hits": [r["row"][0] for r in episodic_res["results"][0]["data"]],
            "raptor_summary": [r["row"][0] for r in raptor_res["results"][0]["data"]],
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
        pass

if __name__ == "__main__":
    main()
