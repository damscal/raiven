{ pkgs ? import <nixpkgs> {} }:

let
  pythonEnv = pkgs.python311.withPackages (ps: with ps; [
    requests
    numpy
    neo4j
    mcp
  ]);
in
pkgs.mkShell {
  buildInputs = [
    pythonEnv
  ];

  shellHook = ''
    echo "--- RAIVEN Troubleshooting Environment ---"
    export RAIVEN_NEO4J_URI="https://server1os1.oneira.pp.ua/neo4j/"
    export RAIVEN_OLLAMA_HOST="https://server1os1.oneira.pp.ua/ollama/"
    export RAIVEN_OLLAMA_MODEL="embeddinggemma:latest"
    export RAIVEN_VECTOR_DIMENSIONS=768
    
    # Secrets
    export RAIVEN_NEO4J_USER="neo4j"
    export RAIVEN_NEO4J_PASSWORD_FILE="/home/damscal/.config/sops-nix/secrets/server1os1-neo4j-password"
    export RAIVEN_NEO4J_API_KEY_FILE="/home/damscal/.config/sops-nix/secrets/server1os1-neo4j-api-key"
    export RAIVEN_OLLAMA_API_KEY_FILE="/home/damscal/.config/sops-nix/secrets/server1os1-ollama-api-key"
    
    echo "Environment variables set. Use 'python test_connections.py' or 'python raiven.py' to test."
  '';
}
