import time
import sys
import os
import logging

# Configure logging at module level for entry point compatibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

from . import CognitiveMemory

logger = logging.getLogger("raiven_metabolism")

def run_metabolism_cycle():
    """
    Main loop for the background metabolism process.
    It processes embeddings, cognitive dissonance, and RAPTOR summarization
    at a slow pace to avoid overloading the server.
    """
    logger = logging.getLogger("raiven_metabolism")
    logger.info("Raiven Metabolism Process Started")
    
    # Initialize brain connection
    try:
        brain = CognitiveMemory()
        logger.info("Connected to CognitiveMemory")
    except Exception as e:
        logger.error(f"Failed to connect to memory: {e}")
        return

    while True:
        try:
            # 1. Process Pending Embeddings (Highest Priority for Search)
            # Check if there are chunks needing embedding
            result = brain._query_neo4j("""
                MATCH (c:Chunk {needs_embedding: true})
                RETURN count(c) as count
            """)
            
            # Defensive check for Neo4j response structure
            if not result or "results" not in result or not result["results"]:
                logger.warning("Empty or invalid result from Neo4j")
                time.sleep(30)
                continue
                
            pending_emb = result["results"][0]["data"][0]["row"][0]
            
            if pending_emb > 0:
                logger.info(f"Processing 1 of {pending_emb} pending embeddings...")
                try:
                    brain._process_pending_embeddings(limit=1)
                except Exception as e:
                    logger.error(f"Embedding failed (server might be busy): {e}")
                
                # Longer sleep to let CPU cool down
                time.sleep(15)
                continue # Loop back to prioritize embeddings

            # 2. Resolve Cognitive Dissonance (Medium Priority)
            # Check for unchecked chunks
            result_diss = brain._query_neo4j("""
                MATCH (c:Chunk)
                WHERE c.dissonance_checked IS NULL AND NOT c.needs_embedding
                RETURN count(c) as count
            """)
            
            if not result_diss or "results" not in result_diss or not result_diss["results"]:
                pending_diss = 0
            else:
                pending_diss = result_diss["results"][0]["data"][0]["row"][0]
            
            if pending_diss > 0:
                logger.info(f"Analyzing dissonance for 1 of {pending_diss} chunks...")
                brain._resolve_cognitive_dissonance() # Processes 1 chunk internally
                # Significant sleep after LLM usage
                time.sleep(20)
                continue

            # 3. RAPTOR Summarization (Low Priority)
            # Only run if no other tasks are pending
            # We can implement a check to see if enough new chunks exist to warrant a summary
            # For now, we just run the update check occasionally
            logger.info("Checking RAPTOR tree updates...")
            brain._update_raptor_tree()
            
            # If we got here, the system is mostly up to date. Long sleep.
            logger.info("System up to date. Sleeping...")
            
            # Update heartbeat in Neo4j
            try:
                brain._query_neo4j("""
                    MERGE (h:Heartbeat {id: 'metabolism'})
                    SET h.last_seen = datetime(),
                        h.status = 'active'
                """)
            except Exception as e:
                logger.error(f"Failed to update heartbeat: {e}")
                
            time.sleep(60)

        except Exception as e:
            logger.error(f"Error in metabolism cycle: {e}")
            time.sleep(60) # Wait on error

def main():
    # Ensure we can import raiven package
    run_metabolism_cycle()

if __name__ == "__main__":
    main()
