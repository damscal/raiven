import sys
import os
import logging

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
# We delay initialization to prevent crashes if env vars are missing during discovery
brain = None

def get_brain():
    global brain
    if brain is None:
        logger.debug("Initializing CognitiveMemory core...")
        try:
            brain = CognitiveMemory()
            logger.debug("CognitiveMemory core initialized successfully.")
        except Exception as e:
            # IMPORTANT: Do not use logger.exception here if it could print to stdout
            # instead, explicitly print to stderr
            import traceback
            traceback.print_exc(file=sys.stderr)
            raise
    return brain

@mcp.tool()
def add_memory(text: str, role: str = "user") -> str:
    """
    Ingest a new memory into the Holographic Cognitive Memory System.
    This stores the text as a chunk, extracts entities, and updates the RAPTOR tree.
    """
    logger.debug(f"Tool add_memory called with text: {text[:20]}...")
    try:
        get_brain().add_memory(text, role=role)
        return f"Successfully stored memory: {text[:50]}..."
    except Exception as e:
        logger.exception("Error in add_memory tool")
        return f"Error storing memory: {str(e)}"

@mcp.tool()
def retrieve_memory(query: str, top_k: int = 3) -> str:
    """
    Retrieve relevant context from memory based on a query.
    Returns episodic hits, abstractive summaries, and relational facts.
    """
    logger.debug(f"Tool retrieve_memory called with query: {query}")
    try:
        results = get_brain().retrieve(query, top_k=top_k)
        
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
