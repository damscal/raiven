# RAIVEN: Holographic Cognitive Memory System (HCMS)

RAIVEN is a Nix-flaked Python application that implements a Holographic Cognitive Memory System (HCMS). It provides a GraphRAG + RAPTOR architecture for long-term, structured, and abstractive memory for Large Language Models (LLMs), using Neo4j as the graph-vector database and Ollama for embeddings.

## Features

- **GraphRAG + RAPTOR**: Combines graph-based retrieval with recursive abstractive processing for multi-level memory access.
- **Holographic Retrieval**: Simultaneously queries specific details, abstract concepts, and relational facts.
- **Nix Flake**: Reproducible builds and deployments via Nix.
- **Home Manager Service**: Seamless integration with Home Manager for background service management.
- **Secure Configuration**: Uses environment variables and file-based secrets (compatible with `sops-nix`).

## Prerequisites

- [Nix](https://nixos.org/download.html) with flakes enabled.
- [Home Manager](https://nix-community.github.io/home-manager/) (for service deployment).
- Access to a Neo4j 5.x+ instance with vector index support.
- Access to an Ollama instance with an embedding model (e.g., `embeddinggemma:latest`).

## Installation & Usage

### As a Nix Package

To build and run the package directly:

```bash
nix run
```

### As a Home Manager Service

1. Add RAIVEN as an input to your Home Manager flake:

   ```nix
   {
     inputs = {
       # ... other inputs ...
       raiven.url = "path/to/raiven/directory"; # Or a git URL
     };
   }
   ```

2. Import the RAIVEN module in your Home Manager configuration and configure the service:

   ```nix
   { inputs, pkgs, ... }: {
     imports = [ inputs.raiven.homeManagerModules.default ];

     services.raiven = {
       enable = true;
       package = inputs.raiven.packages.${pkgs.system}.default;

       # Nested configuration options
       config = {
         neo4j = {
           uri = "your_neo4j_uri";
           user = "your_neo4j_user";
           passwordFile = "/path/to/neo4j_password_file"; # Optional
           apiKeyFile = "/path/to/neo4j_api_key_file";    # Optional
         };

         ollama = {
           host = "your_ollama_host";
           apiKeyFile = "/path/to/ollama_api_key_file";
           model = {
             name = "embeddinggemma:latest";
             vectorDimensions = 768;
           };
         };
       };
     };
   }
   ```

3. Rebuild and switch your Home Manager configuration:

   ```bash
   home-manager switch
   ```

## Configuration

RAIVEN is configured entirely through Home Manager options (as shown above) or environment variables (for non-service use).

### Environment Variables (for direct execution)

- `RAIVEN_NEO4J_URI`: Neo4j connection URI.
- `RAIVEN_NEO4J_USER`: Neo4j username.
- `RAIVEN_NEO4J_PASSWORD_FILE`: Path to file containing Neo4j password.
- `RAIVEN_NEO4J_API_KEY_FILE`: Path to file containing Neo4j API key (optional).
- `RAIVEN_OLLAMA_HOST`: Ollama host URI.
- `RAIVEN_OLLAMA_API_KEY_FILE`: Path to file containing Ollama API key.
- `RAIVEN_OLLAMA_MODEL`: Ollama model name.
- `RAIVEN_VECTOR_DIMENSIONS`: Vector dimensions.

Secret files are read by the application, and paths can contain `~` which will be expanded.

## Project Structure

- `raiven.py`: Core Python application logic.
- `pyproject.toml`: Python package metadata.
- `flake.nix`: Nix flake definition for packaging and development environment.
- `hm-module.nix`: Home Manager module for the systemd service.
- `implementation guide.md`: Technical details of the HCMS architecture.
- `USAGE.md`: Detailed usage instructions.
- `CONTRIBUTING.md`: Guidelines for contributing to the project.
