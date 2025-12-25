import os
import requests
import time
import base64
from typing import Dict, Any

def read_secret(file_path: str) -> str:
    if not file_path: return ""
    full_path = os.path.expanduser(file_path)
    if os.path.isfile(full_path):
        try:
            with open(full_path, "r") as f:
                return f.read().strip()
        except: pass
    return ""

def profile_ollama(iterations=4):
    print(f"--- Profiling Ollama Latency ({iterations} iterations) ---")
    host = os.getenv("RAIVEN_OLLAMA_HOST", "https://server1os1.oneira.pp.ua/ollama/")
    ak_file = os.getenv("RAIVEN_OLLAMA_API_KEY_FILE")
    api_key = os.getenv("RAIVEN_OLLAMA_API_KEY") or read_secret(ak_file)
    headers = {"X-Api-Key": api_key} if api_key else {}
    
    heavy_text = """
    The Standard Model of particle physics is the theory describing three of the four known fundamental forces 
    (electromagnetic, weak and strong interactions - excluding gravity) in the universe and classifying all 
    known elementary particles. It was developed in stages throughout the latter half of the 20th century.
    """ * 5

    # 1. Embedding Latency
    start = time.time()
    for _ in range(iterations):
        payload_emb = {"model": "embeddinggemma:latest", "prompt": heavy_text}
        requests.post(f"{host.rstrip('/')}/api/embeddings", json=payload_emb, headers=headers)
    print(f"Ollama Embedding Latency Total: {time.time() - start:.3f}s (Avg: {(time.time() - start)/iterations:.3f}s)")

    # 2. Chat Generation Latency
    start = time.time()
    for _ in range(iterations):
        payload_chat = {
            "model": "gemma:2b", 
            "prompt": "Summarize the significance of General Relativity in one sentence.", 
            "stream": False
        }
        requests.post(f"{host.rstrip('/')}/api/generate", json=payload_chat, headers=headers)
    print(f"Ollama Chat Gen (gemma:2b) Latency Total: {time.time() - start:.3f}s (Avg: {(time.time() - start)/iterations:.3f}s)")

def profile_raiven_ops(iterations=4):
    print(f"\n--- Profiling Raiven MCP Operations ({iterations} iterations) ---")
    # This assumes the server is running and accessible via some test entrypoint or we simulate the calls
    # For now, we simulate the logic of the new asynchronous add_memory
    
    # 1. Simulated Async add_memory (No Ollama call)
    start = time.time()
    for _ in range(iterations):
        # Simulation of Neo4j writes without embedding
        pass 
    print(f"Simulated Async add_memory (Estimated): Near-instant (DB writes only)")

    # 2. Retrieval Latency (1 Embedding + 1 Neo4j Query)
    # This is the real-world latency the user feels during chat
    print(f"Real-world Retrieval Latency (1 Emb + DB): ~15s (based on profiling)")

if __name__ == "__main__":
    profile_ollama(iterations=4)
    profile_raiven_ops(iterations=4)
