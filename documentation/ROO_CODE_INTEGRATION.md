# Roo Code Integration with Raiven (Docker-based MCP)

This guide explains how to enable Roo Code to use Raiven as its long-term memory using Docker.

## 1. Setup

### Build the Docker Image
To ensure Raiven is portable across all your devices, we use a Docker-based MCP server. Run this in the root of the Raiven repository:

```bash
docker build -t raiven-mcp .
```

### Configuration
The MCP server is registered in your Roo Code settings. It runs the container in "interactive" mode to communicate via `stdio`.

**`mcp_settings.json` entry:**
```json
"raiven": {
  "command": "docker",
  "args": ["run", "-i", "--rm", "raiven-mcp"],
  "env": {
    "RAIVEN_NEO4J_URI": "https://server1os1.oneira.pp.ua/neo4j/",
    "RAIVEN_OLLAMA_HOST": "https://server1os1.oneira.pp.ua/ollama/",
    "RAIVEN_OLLAMA_MODEL": "embeddinggemma:latest"
  }
}
```

## 2. Using the Tools

Once the MCP server is connected, Roo Code will have access to two new tools:

### `add_memory`
Use this tool to store important context or project milestones.
*   **Input:** `text` (The content to remember), `role` (Optional: "user" or "assistant").
*   **Example Prompt:** *"Remember that we switched the Neo4j API to the REST endpoint because of proxy issues."*

### `retrieve_memory`
Use this tool to recall past context.
*   **Input:** `query` (Search string), `top_k` (Optional number of results).
*   **Example Prompt:** *"Search my memory for Neo4j proxy configuration."*

### `list_memory_profiles`
List all available database profiles in the Neo4j instance.
*   **Example Prompt:** *"What memory profiles do I have?"*

### `switch_memory_profile`
Switch to a different memory database to keep contexts separate.
*   **Input:** `profile_name` (Name of the database).
*   **Example Prompt:** *"Switch to the 'raiventest' memory profile."*

### `create_memory_profile`
Create a new isolated memory profile.
*   **Input:** `profile_name`.
*   **Example Prompt:** *"Create a new memory profile for Project X."*

### `remove_memory_profile`
Permanently delete an existing memory profile.
*   **Input:** `profile_name`.
*   **Example Prompt:** *"Remove the 'raiventest' profile."*

## 3. Benefits of Docker Integration

*   **Portability**: Works on NixOS, Ubuntu, macOS, and Windows without local Python dependencies.
*   **Isolation**: No conflicts with local library versions.
*   **Device-Agnostic**: As long as the `raiven-mcp` image is built on the device, Roo Code can use it instantly.

---
*For core architecture details, see the [Implementation Guide](./implementation%20guide.md).*
