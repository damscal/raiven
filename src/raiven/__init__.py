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
NEO4J_URI = get_config("RAIVEN_NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = get_config("RAIVEN_NEO4J_USER", "neo4j")
# Try RAIVEN_NEO4J_PASSWORD first (for Docker/baking), then fallback to RAIVEN_NEO4J_PASSWORD_FILE
NEO4J_PASSWORD = get_config("RAIVEN_NEO4J_PASSWORD") or read_secret(get_config("RAIVEN_NEO4J_PASSWORD_FILE"))
NEO4J_DATABASE = get_config("RAIVEN_NEO4J_DATABASE") # Default to None to use system default if not set

OLLAMA_HOST = get_config("RAIVEN_OLLAMA_HOST", "http://localhost:11434")
OLLAMA_API_KEY = get_config("RAIVEN_OLLAMA_API_KEY") or read_secret(get_config("RAIVEN_OLLAMA_API_KEY_FILE"))
EMBEDDING_MODEL = get_config("RAIVEN_OLLAMA_MODEL", "embeddinggemma:latest")
CHAT_MODEL = get_config("RAIVEN_OLLAMA_CHAT_MODEL", "gemma:2b") 
SUBCONSCIOUS_MODEL = get_config("RAIVEN_OLLAMA_SUBCONSCIOUS_MODEL", "gemma:2b") # Reverted to gemma:2b for stability
VECTOR_DIMENSIONS = int(get_config("RAIVEN_VECTOR_DIMENSIONS", "768"))

class CognitiveMemory:
    def __init__(self, database: str = None):
        self.database = database or NEO4J_DATABASE or "neo4j"
        # Check if URI is bolt or http
        if NEO4J_URI.startswith("bolt"):
             self.neo4j_url = NEO4J_URI # Bolt uses its own protocol
        else:
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

    def _query_neo4j(self, cypher: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executes a Cypher query via the Neo4j REST API or Bolt.
        """
        if self.neo4j_url.startswith("bolt"):
            from neo4j import GraphDatabase
            # We use a context manager for the driver if we were in a long-lived app,
            # but for simplicity in this REST-compatible structure, we create it.
            # In a production environment with Bolt, using the official driver is better.
            with GraphDatabase.driver(self.neo4j_url, auth=(NEO4J_USER, NEO4J_PASSWORD)) as driver:
                with driver.session(database=self.database) as session:
                    result = session.run(cypher, parameters or {})
                    # Format to match the REST API response structure expected by other methods
                    data = {"results": [{"columns": [], "data": []}], "errors": []}
                    for record in result:
                        data["results"][0]["data"].append({"row": list(record.values())})
                    return data

        payload = {
            "statements": [
                {
                    "statement": cypher,
                    "parameters": parameters or {}
                }
            ]
        }
        response = requests.post(self.neo4j_url, json=payload, headers=self.neo4j_headers)
        response.raise_for_status()
        
        data = response.json()
        if data.get("errors"):
            raise Exception(f"Neo4j Error: {data['errors']}")
        return data

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
            # Increased timeout for embedding to handle slower models
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()["embedding"]
        except Exception as e:
            # We log to stderr and re-raise
            import sys
            print(f"Error calling Ollama: {e}", file=sys.stderr)
            raise

    def _chat(self, prompt: str, model: str = None) -> str:
        """
        Generates a completion using the configured chat model.
        """
        target_model = model or CHAT_MODEL
        url = f"{OLLAMA_HOST.rstrip('/')}/api/generate"
        headers = {"X-Api-Key": OLLAMA_API_KEY} if OLLAMA_API_KEY else {}
        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            print(f"Error calling Ollama Chat ({target_model}): {e}")
            return ""

    def add_memory(self, text: str, role: str = "user", entities: List[str] = None):
        chunk_id = str(uuid.uuid4())
        
        # --- Entity Extraction Strategy ---
        if entities:
            extracted_entities = entities
        else:
            extracted_entities = [word.strip(".,!?") for word in text.split() if word[0].isupper() and len(word) > 1] 

        # We store the chunk WITHOUT embedding first to make the call near-instant
        query_chunk = """
        CREATE (c:Chunk {
            id: $id, 
            text: $text, 
            role: $role, 
            timestamp: datetime(),
            needs_embedding: true
        })
        """
        self._query_neo4j(query_chunk, {"id": chunk_id, "text": text, "role": role})

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
            ON CREATE SET r.weight = 2.0
            ON MATCH SET r.weight = r.weight + 1.0
            """
            self._query_neo4j(query_rel, {"chunk_id": chunk_id})

        self.prune_weak_connections(threshold=0.5)

    def log_session_message(self, session_id: str, session_name: str, text: str, role: str):
        """
        Records a message into a specific session log, isolated from main knowledge.
        """
        message_id = str(uuid.uuid4())
        cypher = """
        MERGE (s:Session {id: $sid})
        ON CREATE SET s.name = $sname, s.started_at = datetime()
        
        CREATE (m:MessageLog {
            id: $mid,
            text: $text,
            role: $role,
            timestamp: datetime()
        })
        
        MERGE (s)-[:HAS_MESSAGE]->(m)
        
        WITH s, m
        MATCH (s)-[:HAS_MESSAGE]->(prev:MessageLog)
        WHERE prev <> m
        WITH m, prev
        ORDER BY prev.timestamp DESC
        LIMIT 1
        MERGE (prev)-[:NEXT_MESSAGE]->(m)
        """
        self._query_neo4j(cypher, {
            "sid": session_id,
            "sname": session_name,
            "mid": message_id,
            "text": text,
            "role": role
        })

    def trigger_consolidation(self):
        """
        Manually triggers embedding generation for pending chunks,
        checks for cognitive dissonance, and updates RAPTOR summarization.
        """
        self._process_pending_embeddings()
        self._resolve_cognitive_dissonance()
        self._update_raptor_tree()

    def _resolve_cognitive_dissonance(self):
        """
        Analyzes recent chunks for potential contradictions with existing knowledge
        using the internal LLM.
        """
        # Find chunks that haven't been checked for dissonance yet
        result = self._query_neo4j("""
            MATCH (c:Chunk)
            WHERE c.dissonance_checked IS NULL AND NOT c.needs_embedding
            RETURN c.id as id, c.text as text
            LIMIT 5
        """)
        
        rows = result["results"][0]["data"]
        for r in rows:
            cid, text = r["row"][0], r["row"][1]
            
            # Find potentially related information in the graph
            context = self.retrieve(text, top_k=2)
            existing_knowledge = "\n".join(context["episodic_hits"])
            
            if not existing_knowledge:
                self._query_neo4j("MATCH (c:Chunk {id: $id}) SET c.dissonance_checked = true", {"id": cid})
                continue

            prompt = f"""
            Analyze the following NEW information against the EXISTING knowledge.
            Identify if there are direct contradictions or significant inconsistencies.
            
            EXISTING KNOWLEDGE:
            {existing_knowledge}
            
            NEW INFORMATION:
            {text}
            
            If there is a contradiction, explain it briefly. If they are consistent, reply 'CONSISTENT'.
            """
            
            analysis = self._chat(prompt, model=SUBCONSCIOUS_MODEL)
            
            if "CONSISTENT" not in analysis.upper():
                # Mark potential dissonance without automatically weakening connections.
                # It is Malik's (active consciousness) responsibility to review these.
                import sys
                print(f">> Potential Cognitive Dissonance flagged in {cid} using {SUBCONSCIOUS_MODEL}", file=sys.stderr)
                self._query_neo4j("""
                    MATCH (c:Chunk {id: $id})
                    SET c.dissonance_checked = true, 
                        c.potential_dissonance = true, 
                        c.dissonance_report = $report
                """, {"id": cid, "report": analysis})
            else:
                self._query_neo4j("MATCH (c:Chunk {id: $id}) SET c.dissonance_checked = true", {"id": cid})

    def _process_pending_embeddings(self, limit: int = 10):
        """
        Finds chunks that need embeddings, generates them, and updates Neo4j.
        Gives up after 3 failed attempts to prevent infinite retries.
        """
        result = self._query_neo4j("""
            MATCH (c:Chunk {needs_embedding: true})
            RETURN c.id as id, c.text as text, coalesce(c.failed_attempts, 0) as failed
            ORDER BY c.timestamp ASC
            LIMIT $limit
        """, {"limit": limit})

        rows = result["results"][0]["data"]
        for r in rows:
            cid, text, failed = r["row"][0], r["row"][1], r["row"][2]
            try:
                embedding = self._embed(text)
                self._query_neo4j("""
                    MATCH (c:Chunk {id: $id})
                    SET c.embedding = $emb, c.needs_embedding = false, c.failed_attempts = null
                """, {"id": cid, "emb": embedding})
                import sys
                print(f">> Generated embedding for chunk: {cid}", file=sys.stderr)
            except Exception as e:
                failed += 1
                if failed >= 3:
                    # Give up after 3 attempts
                    self._query_neo4j("""
                        MATCH (c:Chunk {id: $id})
                        SET c.needs_embedding = false, c.failed_attempts = $failed
                    """, {"id": cid, "failed": failed})
                    import sys
                    print(f">> Gave up embedding for chunk: {cid} after {failed} attempts", file=sys.stderr)
                else:
                    # Increment failed count
                    self._query_neo4j("""
                        MATCH (c:Chunk {id: $id})
                        SET c.failed_attempts = $failed
                    """, {"id": cid, "failed": failed})
                    import sys
                    print(f"Error generating embedding for {cid}: {e} (attempt {failed})", file=sys.stderr)

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

        # --- Advanced Summarization via LLM ---
        combined_text = " ".join([c['text'] for c in chunks])
        prompt = f"""
        Summarize the following text into a concise, high-level abstract.
        Text: {combined_text}
        """
        summary_text = self._chat(prompt)
        if not summary_text:
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

    def forget_memory(self, chunk_id: str):
        """
        Removes a specific chunk and prunes orphan entities/relationships.
        """
        # 1. Delete the chunk and its mentions
        self._query_neo4j("""
            MATCH (c:Chunk {id: $id})
            DETACH DELETE c
        """, {"id": chunk_id})
        
        # 2. Prune entities that no longer have any mentions
        self._query_neo4j("""
            MATCH (e:Entity)
            WHERE NOT (e)<-[:MENTIONS]-(:Chunk)
            DETACH DELETE e
        """)
        
        # 3. TODO: Recalculate RAPTOR summaries if needed
        import sys
        print(f">> Pruned memory chunk: {chunk_id}", file=sys.stderr)

    def prune_weak_connections(self, threshold: float = 0.5):
        """
        Removes relationships that have decayed below a threshold and prunes orphan entities.
        """
        # Delete weak relationships
        self._query_neo4j("""
            MATCH ()-[r:RELATED_TO]->()
            WHERE r.weight <= $threshold
            DELETE r
        """, {"threshold": threshold})
        
        # Prune orphaned entities (no mentions AND no relationships)
        self._query_neo4j("""
            MATCH (e:Entity)
            WHERE NOT (e)<-[:MENTIONS]-(:Chunk) 
              AND NOT (e)-[:RELATED_TO]-()
            DETACH DELETE e
        """)

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

        # --- Hybrid Search: Keyword Extraction via LLM ---
        # Optimized: Use heuristic extraction for speed, fallback to LLM only if needed
        # For now, we stick to heuristic to avoid latency on retrieval
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
