import os
import requests
import base64

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

def test_ollama():
    print("--- Testing Ollama (REST API) ---")
    host = os.getenv("RAIVEN_OLLAMA_HOST")
    ak_file = os.getenv("RAIVEN_OLLAMA_API_KEY_FILE")
    
    api_key = read_secret(ak_file)
    headers = {"X-Api-Key": api_key} if api_key else {}
    
    try:
        url = f"{host.rstrip('/')}/api/tags"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"SUCCESS: Ollama accessible at {host}")
        else:
            print(f"FAILURE: Status {response.status_code} at {url}")
        
    except Exception as e:
        print(f"FAILURE: Ollama test failed: {e}")

def test_neo4j():
    print("\n--- Testing Neo4j (REST API) ---")
    uri = os.getenv("RAIVEN_NEO4J_URI")
    user = os.getenv("RAIVEN_NEO4J_USER", "neo4j")
    pw_file = os.getenv("RAIVEN_NEO4J_PASSWORD_FILE")
    
    password = os.getenv("RAIVEN_NEO4J_PASSWORD") or read_secret(pw_file)

    # We use the standard path. The improved proxy maps /neo4j/ to Neo4j root.
    url = f"{uri.rstrip('/')}/db/neo4j/tx/commit"
    print(f"Targeting endpoint: {url}")
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    if user and password:
        auth_str = f"{user}:{password}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()
        headers["Authorization"] = f"Basic {encoded_auth}"
        print("Included Basic Auth header.")

    else:
        print(f"Auth DEBUG: user='{user}'")
        print(f"Auth DEBUG: uri='{uri}'")
        print(f"Auth DEBUG: pw_file='{pw_file}'")
        print(f"Auth DEBUG: env_pw_set={bool(os.getenv('RAIVEN_NEO4J_PASSWORD'))}")
        print(f"Auth DEBUG: password_len={len(password) if password else 0}")

    try:
        payload = {"statements": [{"statement": "RETURN 1 as val"}]}
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print("SUCCESS: Connected to Neo4j.")
            return True
        else:
            print(f"FAILURE: Status {response.status_code} at {url}")
            print(f"Response Body: {response.text}")
            
    except Exception as e:
        print(f"FAILURE: Neo4j test failed: {e}")

    return False

if __name__ == "__main__":
    test_ollama()
    test_neo4j()
