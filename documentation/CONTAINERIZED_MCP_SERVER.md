# Containerized MCP Server Feature

The Raiven project provides a containerized MCP server that can be run using either Podman or Docker. This allows for better isolation and easier deployment while maintaining all the functionality of the Raiven MCP server.

## Overview

**Important**: MCP servers are designed to be launched on-demand by MCP clients (like Roo Code) and should not run as persistent services. The Home Manager module provides package installation, but the actual server execution should be handled by your MCP client.

This approach provides several advantages:

- Isolated execution environment
- Consistent deployment across different systems
- Automatic image management
- Support for both Podman and Docker runtimes

## Configuration

The Home Manager module provides package installation for the Raiven MCP server.

### `services.raiven.enable`

Enables the Raiven Home Manager module.

- **Type**: Boolean
- **Default**: `false`
- **Description**: When set to `true`, installs the Raiven package.

### `services.raiven.package`

- **Type**: Package
- **Description**: The Raiven package to use.

## How to Use

### 1. Install Packages via Home Manager

Add the Raiven package to your Home Manager configuration:

```nix
{ inputs, ... }: {
  services.raiven = {
    enable = true;
    package = inputs.raiven.packages.x86_64-linux.default;
  };

  # The package will be available in your environment
  home.packages = [ inputs.raiven.packages.x86_64-linux.default ];
}
```

**Note**: Replace `x86_64-linux` with your actual system architecture (e.g., `aarch64-linux`, `x86_64-darwin`, etc.).

### 2. Automatic Docker Image Setup

The Home Manager module automatically builds and loads the latest Raiven MCP Docker image during system activation. The `raiven-docker-setup` service will:

- Always build the most recent Docker image using Nix
- Remove any existing `raiven-mcp:latest` image
- Load the fresh image into your container runtime (Podman or Docker)

This ensures you always have the latest version of the Raiven MCP server and happens automatically when you rebuild your Home Manager configuration.

### 3. Configure in MCP Client

Configure the Raiven MCP server directly in your MCP client (Roo Code) settings:

```json
{
  "mcpServers": {
    "raiven": {
      "command": "podman",
      "args": ["run", "-i", "--rm", "localhost/raiven-mcp:latest"],
      "env": {
        "RAIVEN_NEO4J_URI": "bolt://localhost:7687",
        "RAIVEN_OLLAMA_HOST": "http://localhost:11434",
        "RAIVEN_OLLAMA_MODEL": "embeddinggemma:latest"
      }
    }
  }
}
```

For Docker instead of Podman:

```json
{
  "mcpServers": {
    "raiven": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "localhost/raiven-mcp:latest"],
      "env": {
        "RAIVEN_NEO4J_URI": "bolt://localhost:7687",
        "RAIVEN_OLLAMA_HOST": "http://localhost:11434",
        "RAIVEN_OLLAMA_MODEL": "embeddinggemma:latest"
      }
    }
  }
}
```

## Troubleshooting

### Image Loading Issues

If the image fails to load, ensure that:
1. The Docker image was built and loaded correctly
2. The container runtime (Podman/Docker) is properly installed and accessible
3. The user has permissions to run containers

### Configuration Issues

Make sure all required configuration values (Neo4j URI, Ollama host, etc.) are properly set in your MCP client configuration.

## Security Considerations

- The container runs with minimal privileges
- Sensitive information like passwords and API keys should be provided via environment variables
- The container doesn't expose network ports unnecessarily, communicating via stdio with the MCP client