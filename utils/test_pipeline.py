import os
import sys

# Add the parent directory to sys.path so we can import raiven
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from raiven import CognitiveMemory

def run_test():
    # Force test database via environment variable
    os.environ["RAIVEN_NEO4J_DATABASE"] = "raiventest"
    
    print("--- RAIVEN TEST SUITE ---")
    brain = CognitiveMemory()
    
    try:
        # 1. Clear test database (BE CAREFUL)
        print("Clearing test database...")
        brain._query_neo4j("MATCH (n) DETACH DELETE n")
        
        # 2. Ingest Memories
        memories = [
            "Project Raiven is a holographic cognitive memory system.",
            "It uses Neo4j to store graph-based relationships.",
            "The system implements RAPTOR for recursive summarization.",
            "Ollama provides the embeddings and LLM capabilities.",
            "NixOS is used for the infrastructure as code."
        ]
        
        print(f"Ingesting {len(memories)} memories...")
        for mem in memories:
            print(f"Adding: {mem}")
            brain.add_memory(mem)
            
        print("\n--- Retrieval Test ---")
        queries = [
            "What is Project Raiven?",
            "What database does it use?",
            "Tell me about the infrastructure."
        ]
        
        for q in queries:
            print(f"\nQuery: {q}")
            results = brain.retrieve(q)
            print(f"Episodic: {results['episodic_hits']}")
            print(f"RAPTOR: {results['raptor_summary']}")
            print(f"KG: {results['knowledge_graph']}")
            
    except Exception as e:
        print(f"Test Failed: {e}")
        sys.exit(1)
    finally:
        print("\nTest completed.")

if __name__ == "__main__":
    run_test()
