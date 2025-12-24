import os
import requests
import base64
import sys

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

def change_password(new_password: str):
    uri = os.getenv("RAIVEN_NEO4J_URI")
    user = os.getenv("RAIVEN_NEO4J_USER", "neo4j")
    pw_file = os.getenv("RAIVEN_NEO4J_PASSWORD_FILE")
    
    current_password = read_secret(pw_file)
    
    # Target the system database for user management
    url = f"{uri.rstrip('/')}/db/system/tx/commit"
    
    auth_str = f"{user}:{current_password}"
    encoded_auth = base64.b64encode(auth_str.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {encoded_auth}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # Cypher to change password for the current user
    payload = {
        "statements": [
            {
                "statement": "ALTER CURRENT USER SET PASSWORD FROM $current_pw TO $new_pw",
                "parameters": {
                    "current_pw": current_password,
                    "new_pw": new_password
                }
            }
        ]
    }

    print(f"Attempting to change password for user '{user}'...")
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("errors"):
            print(f"FAILURE: Neo4j returned errors: {data['errors']}")
        else:
            print("SUCCESS: Password changed successfully.")
            print("\nIMPORTANT: You must now update your sops secret file with the new password")
            print(f"Path: {pw_file}")
            
    except Exception as e:
        print(f"FAILURE: Password change failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python change_neo4j_password.py <new_password>")
        sys.exit(1)
        
    change_password(sys.argv[1])
