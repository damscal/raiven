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
def list_memory_profiles() -> str:
    """
    List all available memory profiles (databases) in the system.
    """
    logger.debug("Tool list_memory_profiles called")
    try:
        profiles = get_brain().list_databases()
        return "Available Memory Profiles:\n" + "\n".join([f"- {p}" for p in profiles])
    except Exception as e:
        logger.exception("Error in list_memory_profiles tool")
        return f"Error listing profiles: {str(e)}"

@mcp.tool()
def switch_memory_profile(profile_name: str) -> str:
    """
    Switch the active memory profile (database). 
    This allows you to separate memories for different projects or contexts.
    """
    logger.debug(f"Tool switch_memory_profile called with profile: {profile_name}")
    try:
        get_brain().switch_database(profile_name)
        return f"Successfully switched to memory profile: {profile_name}"
    except Exception as e:
        logger.exception("Error in switch_memory_profile tool")
        return f"Error switching profile: {str(e)}"

""" 
DISABLED BECAUSE THEY NEED NEO4J ENTERPRISE. NEO4J COMMUNITY --> ONLY 1 DATABASE
@mcp.tool()
def create_memory_profile(profile_name: str) -> str:
    """
    Create a new memory profile (Neo4j database).
    """
    logger.debug(f"Tool create_memory_profile called with name: {profile_name}")
    try:
        get_brain().create_database(profile_name)
        return f"Successfully created memory profile: {profile_name}. You can now switch to it using switch_memory_profile."
    except Exception as e:
        logger.exception("Error in create_memory_profile tool")
        return f"Error creating profile: {str(e)}"

@mcp.tool()
def remove_memory_profile(profile_name: str) -> str:
    """
    Permanently remove a memory profile (Neo4j database).
    WARNING: This will delete all memories stored in that profile.
    """
    logger.debug(f"Tool remove_memory_profile called with name: {profile_name}")
    try:
        if profile_name == "neo4j":
            return "Error: Cannot remove the default 'neo4j' profile."
        get_brain().drop_database(profile_name)
        return f"Successfully removed memory profile: {profile_name}"
    except Exception as e:
        logger.exception("Error in remove_memory_profile tool")
        return f"Error removing profile: {str(e)}" 
"""

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
