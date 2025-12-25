import sys
import os
import logging
import subprocess
import json

# Configure logging to stderr
logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
logger = logging.getLogger("raiven_mcp")

# FastMCP doesn't strictly need this if installed as package, 
# but for Docker/direct run it helps.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP
from raiven import CognitiveMemory

# Initialize FastMCP server
mcp = FastMCP("Raiven Memory System")

# Initialize the memory core
brain = None

def get_brain():
    global brain
    if brain is None:
        logger.debug("Initializing CognitiveMemory core...")
        try:
            brain = CognitiveMemory()
            logger.debug("CognitiveMemory core initialized successfully.")
        except Exception as e:
            import traceback
            traceback.print_exc(file=sys.stderr)
            raise
    return brain

@mcp.tool()
def check_and_start_metabolism() -> str:
    """
    Checks if the Subconscious Metabolism process is running and starts it if not.
    """
    logger.debug("Tool check_and_start_metabolism called")
    try:
        # Check if the metabolism process is running (searching for the script name)
        # Using pgrep -f to match the full command line
        try:
            result = subprocess.run(["pgrep", "-f", "raiven_metabolism.py"], capture_output=True, text=True)
            if result.returncode == 0:
                pids = result.stdout.strip().split()
                return f"Subconscious Metabolism is already active (PIDs: {', '.join(pids)})."
        except FileNotFoundError:
            # pgrep might not be available in some minimal environments
            logger.warning("pgrep not found, skipping check and attempting to start.")

        # If not running, attempt to start it
        metabolism_path = os.path.join(os.path.dirname(__file__), "raiven_metabolism.py")
        
        # We use Popen with setsid or similar to ensure it survives if the MCP server restarts
        # depending on the environment. In Docker, it's simpler to run as a separate container,
        # but this tool provides a safety valve.
        subprocess.Popen([sys.executable, metabolism_path], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL,
                         start_new_session=True)
        
        return "Subconscious Metabolism was not active. Successfully triggered it in the background."
    except Exception as e:
        logger.exception("Error in check_and_start_metabolism tool")
        return f"Error checking/starting metabolism: {str(e)}"

@mcp.tool()
def add_memory(text: str, role: str = "user", entities: list[str] = None) -> str:
    """
    Ingest a new memory into the Holographic Cognitive Memory System.
    This stores the text as a chunk, extracts entities, and updates the RAPTOR tree.
    
    Args:
        text: The content of the memory to store.
        role: The role of the memory creator (default: "user").
        entities: Optional list of entities (people, places, concepts) extracted by the caller.
                  If provided, skips internal LLM extraction to save resources.
    """
    logger.debug(f"Tool add_memory called with text: {text[:20]}...")
    try:
        get_brain().add_memory(text, role=role, entities=entities)
        return f"Successfully stored memory: {text[:50]}..."
    except Exception as e:
        logger.exception("Error in add_memory tool")
        return f"Error storing memory: {str(e)}"

@mcp.tool()
def retrieve_memory(query: str, top_k: int = 3, fast_mode: bool = True) -> str:
    """
    Retrieve context from memory based on a query.
    
    Args:
        query: The search query.
        top_k: Number of episodic memories to retrieve.
        fast_mode: If True (default), performs a rapid search using only the Knowledge Graph (Keywords).
                   If False, performs a holographic search including Vector and RAPTOR (Slower, requires Ollama).
    """
    logger.debug(f"Tool retrieve_memory called with query: {query}, fast_mode: {fast_mode}")
    try:
        brain = get_brain()
        
        if fast_mode:
            # Rapid Search: Only Knowledge Graph
            # We extract keywords locally using a simple heuristic to stay fast
            keywords = [w.strip(".,!?") for w in query.split() if w[0].isupper() and len(w) > 1]
            graph_context = []
            if keywords:
                res = brain._query_neo4j("""
                    MATCH (e:Entity)
                    WHERE e.name IN $keywords
                    MATCH (e)-[r:RELATED_TO]-(neighbor)
                    RETURN e.name + ' is related to ' + neighbor.name as fact
                    LIMIT 10
                """, {"keywords": keywords})
                graph_context = [r["row"][0] for r in res["results"][0]["data"]]
            
            output = ["### Fast Knowledge Graph Recall (Bypassing AI)"]
            if graph_context:
                for fact in graph_context:
                    output.append(f"- {fact}")
            else:
                output.append("- No direct entity matches found in fast mode.")
            return "\n".join(output)
        
        else:
            # Holographic Search: Vector + RAPTOR + Graph
            results = brain.retrieve(query, top_k=top_k)
            
            output = []
            output.append("### Episodic Memory (Direct Hits)")
            for hit in results["episodic_hits"]:
                output.append(f"- {hit}")
                
            output.append("\n### RAPTOR (Abstractive Context)")
            for summary in results["raptor_summary"]:
                output.append(f"- {summary}")
                
            output.append("\n### Relational Facts (Knowledge Graph)")
            for fact in results["knowledge_graph"]:
                output.append(f"- {fact}")
                
            return "\n".join(output)

    except Exception as e:
        logger.exception("Error in retrieve_memory tool")
        return f"Error retrieving memory: {str(e)}"

@mcp.tool()
def chat_with_memory(prompt: str) -> str:
    """
    Directly chat with the memory system using the configured LLM.
    This allows for reasoning over stored knowledge without external processing.
    """
    logger.debug(f"Tool chat_with_memory called with prompt: {prompt[:20]}...")
    try:
        # 1. Retrieve context first
        brain = get_brain()
        context = brain.retrieve(prompt, top_k=3)
        
        # 2. Check for flagged dissonance in retrieved context
        # We search if any of the episodic hits are marked with potential_dissonance
        result_diss = brain._query_neo4j("""
            MATCH (c:Chunk)
            WHERE c.text IN $hits AND c.potential_dissonance = true
            RETURN c.text as text, c.dissonance_report as report
        """, {"hits": context["episodic_hits"]})
        
        dissonance_warnings = ""
        if result_diss["results"][0]["data"]:
            dissonance_warnings = "\n--- WARNING: Potential Cognitive Dissonance Detected in Memory ---\n"
            for r in result_diss["results"][0]["data"]:
                dissonance_warnings += f"Memory: {r['row'][0][:50]}...\nIssue: {r['row'][1]}\n"
        
        context_str = "\n".join([
            "Context from Memory:",
            "--- Episodic ---",
            "\n".join(context["episodic_hits"]),
            "--- Summaries ---",
            "\n".join(context["raptor_summary"]),
            "--- Knowledge Graph ---",
            "\n".join(context["knowledge_graph"])
        ])
        
        # 3. Augment prompt
        augmented_prompt = f"""
        You are an AI assistant with access to a long-term memory.
        Use the following context to answer the user's request.
        
        {context_str}
        
        {dissonance_warnings}
        
        User Request: {prompt}
        """
        
        # 4. Generate response using internal LLM
        response = brain._chat(augmented_prompt)
        return response
    except Exception as e:
        logger.exception("Error in chat_with_memory tool")
        return f"Error processing chat: {str(e)}"

@mcp.tool()
def update_memory_chunk(chunk_id: str, new_text: str) -> str:
    """
    Update the text of a specific memory chunk.
    This is useful for correcting information or resolving cognitive dissonance.
    The chunk will be re-embedded and re-evaluated by the background worker.
    """
    logger.debug(f"Tool update_memory_chunk called for id: {chunk_id}")
    try:
        brain = get_brain()
        # Update text and reset flags to trigger re-processing
        brain._query_neo4j("""
            MATCH (c:Chunk {id: $id})
            SET c.text = $text, 
                c.needs_embedding = true, 
                c.dissonance_checked = null, 
                c.potential_dissonance = null,
                c.dissonance_report = null
        """, {"id": chunk_id, "text": new_text})
        return f"Memory chunk {chunk_id} updated. It will be re-processed by the background worker."
    except Exception as e:
        logger.exception("Error in update_memory_chunk tool")
        return f"Error updating memory: {str(e)}"

@mcp.tool()
def resolve_dissonance(chunk_id: str, resolution: str) -> str:
    """
    Resolve a flagged cognitive dissonance for a specific memory chunk.
    
    Args:
        chunk_id: The ID of the chunk flagged with dissonance.
        resolution: The action to take. Options:
                    - "accept": Mark the dissonance as resolved/accepted (keep the memory as is).
                    - "reject": Delete the memory chunk (it was false/incorrect).
                    - "update": Use update_memory_chunk instead to modify the content.
    """
    logger.debug(f"Tool resolve_dissonance called for id: {chunk_id} with resolution: {resolution}")
    try:
        brain = get_brain()
        if resolution.lower() == "accept":
            brain._query_neo4j("""
                MATCH (c:Chunk {id: $id})
                SET c.potential_dissonance = false, 
                    c.dissonance_resolved = true,
                    c.dissonance_report = null
            """, {"id": chunk_id})
            return f"Dissonance for chunk {chunk_id} accepted and resolved."
        elif resolution.lower() == "reject":
            brain.forget_memory(chunk_id)
            return f"Memory chunk {chunk_id} rejected and deleted."
        else:
            return "Invalid resolution option. Use 'accept', 'reject', or use update_memory_chunk tool for modifications."
    except Exception as e:
        logger.exception("Error in resolve_dissonance tool")
        return f"Error resolving dissonance: {str(e)}"

@mcp.tool()
def forget_memory(chunk_id: str) -> str:
    """
    Remove a specific memory chunk and trigger graph pruning.
    Use this if information is known to be false or obsolete.
    """
    logger.debug(f"Tool forget_memory called with id: {chunk_id}")
    try:
        get_brain().forget_memory(chunk_id)
        return f"Memory chunk {chunk_id} has been forgotten and orphaned graph nodes pruned."
    except Exception as e:
        logger.exception("Error in forget_memory tool")
        return f"Error forgetting memory: {str(e)}"

@mcp.tool()
def trigger_consolidation() -> str:
    """
    Manually trigger the RAPTOR summarization process.
    This consolidates recent memory chunks into higher-level abstract summaries.
    Run this periodically or when system load is low.
    """
    logger.debug("Tool trigger_consolidation called")
    try:
        get_brain().trigger_consolidation()
        return "RAPTOR consolidation process triggered successfully."
    except Exception as e:
        logger.exception("Error in trigger_consolidation tool")
        return f"Error triggering consolidation: {str(e)}"

@mcp.tool()
def query_knowledge_graph(cypher: str, parameters: dict = None) -> str:
    """
    Directly query the Neo4j Knowledge Graph using Cypher syntax.
    Bypasses Ollama and vector search for precise, fast relational retrieval.
    
    Args:
        cypher: The Cypher query string.
        parameters: Optional dictionary of parameters for the query.
    """
    logger.debug(f"Tool query_knowledge_graph called with query: {cypher}")
    try:
        brain = get_brain()
        result = brain._query_neo4j(cypher, parameters)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.exception("Error in query_knowledge_graph tool")
        return f"Error executing Cypher query: {str(e)}"

@mcp.tool()
def list_memory_profiles() -> str:
    """
    List all available memory profiles (databases) in the system.
    Note: In Community Edition, only the default 'neo4j' database is available.
    """
    logger.debug("Tool list_memory_profiles called")
    try:
        brain = get_brain()
        return f"Available Memory Profiles:\n- {brain.database} (Neo4j Community Edition: Single Database Mode)"
    except Exception as e:
        logger.exception("Error in list_memory_profiles tool")
        return f"Error listing profiles: {str(e)}"

@mcp.tool()
def switch_memory_profile(profile_name: str) -> str:
    """
    Switch the active memory profile (database). 
    Note: In Community Edition, switching is disabled as only one database exists.
    """
    logger.debug(f"Tool switch_memory_profile called with profile: {profile_name}")
    return "Error: Database switching is not supported in Neo4j Community Edition. Only one memory profile ('neo4j') is available."

def main():
    # FastMCP automatically handles stdio transport
    # We ensure no logging or stray prints ever hit stdout
    import sys
    import logging
    
    # Configure logging to stderr
    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
    
    # Force all prints to stderr
    import builtins
    original_print = builtins.print
    def stderr_print(*args, **kwargs):
        kwargs["file"] = sys.stderr
        original_print(*args, **kwargs)
    builtins.print = stderr_print

    try:
        # Import FastMCP inside main to ensure it uses the overridden print
        from mcp.server.fastmcp import FastMCP
        mcp.run()
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
        logger.exception("MCP Server crashed during run")
        sys.exit(1)

if __name__ == "__main__":
    main()
