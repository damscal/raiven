# Containerized MCP Server Feature

The Raiven project now includes a feature to automatically run the MCP server in a containerized environment using either Podman or Docker. This allows for better isolation and easier deployment while maintaining all the functionality of the Raiven MCP server.

## Overview

The containerized MCP server feature enables users to run the Raiven MCP server inside a Docker/Podman container through a Home Manager module. This provides several advantages:

- Isolated execution environment
- Consistent deployment across different systems
- Automatic image management
- Support for both Podman and Docker runtimes

## New Configuration Options

### `services.raiven.enableContainerMCP`

Enables the containerized Raiven MCP server systemd service.

- **Type**: Boolean
- **Default**: `false`
- **Description**: When set to `true`, starts the Raiven MCP server in a container using the configured container runtime.

### `services.raiven.containerRuntime`

Selects the container runtime to use for the Raiven MCP server.

- **Type**: Enum (`"podman"` or `"docker"`)
- **Default**: `"podman"`
- **Description**: Specifies which container runtime to use. Podman is the default as it doesn't require a daemon and works well in user contexts.

### `services.raiven.package`

- **Type**: Package
- **Description**: The Raiven package to use.

### `services.raiven.dockerImagePackage`

- **Type**: Package
- **Description**: The RAIVEN Docker image package to use for containerized MCP.

## How to Use

### Basic Configuration

To enable the containerized MCP server with default settings (using Podman):

```nix
{
  services.raiven = {
    enableContainerMCP = true;
    package = inputs.raiven.packages.x86_64-linux.default;  # Replace with your system architecture
    dockerImagePackage = inputs.raiven.packages.x86_64-linux.raiven-docker-image;
    config = {
      neo4j = {
        uri = "bolt://localhost:7687";
        user = "neo4j";
        passwordFile = "/path/to/password/file";
      };
      ollama = {
        host = "http://localhost:11434";
      };
    };
  };
}
```

**Note**: Replace `x86_64-linux` with your actual system architecture (e.g., `aarch64-linux`, `x86_64-darwin`, etc.).

### Using Docker Instead of Podman

To use Docker instead of the default Podman:

```nix
{
  services.raiven = {
    enableContainerMCP = true;
    containerRuntime = "docker";
    package = inputs.raiven.packages.x86_64-linux.default;
    dockerImagePackage = inputs.raiven.packages.x86_64-linux.raiven-docker-image;
    config = {
      # ... your configuration
    };
  };
}
```

### Complete Example

Here's a complete example showing how to integrate the containerized MCP server in your Home Manager configuration:

```nix
{ inputs, ... }: {
  services.raiven = {
    enableContainerMCP = true;
    containerRuntime = "podman"; # Default, can be omitted
    package = inputs.raiven.packages.x86_64-linux.default;
    dockerImagePackage = inputs.raiven.packages.x86_64-linux.raiven-docker-image;

    config = {
      neo4j = {
        uri = "bolt://neo4j-server:7687";
        apiUrl = "http://neo4j-server:7474";
        user = "neo4j";
        passwordFile = "~/.local/share/raiven/neo4j-password";
      };

      ollama = {
        host = "http://ollama-server:11434";
        apiKeyFile = "~/.local/share/raiven/ollama-api-key";
        model = {
          name = "embeddinggemma:latest";
          vectorDimensions = 768;
        };
      };
    };
  };

  # Make sure to add the raiven package to your environment
  home.packages = [ inputs.raiven.packages.x86_64-linux.default ];
}
```

## How It Works

1. When `enableContainerMCP` is set to `true`, the module creates a systemd user service named `raiven-container-mcp.service`.

2. The service automatically loads the pre-built Docker image from the specified `dockerImagePackage`.

3. The service runs the container with the proper environment variables configured based on your `services.raiven.config` settings.

4. The containerized MCP server communicates via stdio, making it compatible with MCP clients like Roo Code.

## Image Management

The Docker image is built automatically as part of the Raiven package build process. The systemd service:

- Checks if the `raiven-mcp:latest` image exists in the container runtime
- If not found, loads the image from the Nix store using the pre-built image in the package's passthru attributes
- Runs the container with proper environment configuration
- Handles stdio communication required for MCP protocol

## Troubleshooting

### Service Not Starting

Check the service status:
```bash
systemctl --user status raiven-container-mcp
```

View logs for more details:
```bash
journalctl --user -u raiven-container-mcp -f
```

### Image Loading Issues

If the image fails to load, ensure that:
1. The `dockerImagePackage` option is correctly set to the Raiven Docker image package
2. The container runtime (Podman/Docker) is properly installed and accessible
3. The user has permissions to run containers

### Configuration Issues

Make sure all required configuration values (Neo4j URI, Ollama host, etc.) are properly set in `services.raiven.config`.

## Migration from Previous Versions

If you were previously using the non-containerized MCP server, you can simply switch by enabling `enableContainerMCP` and disabling the old service if it exists, though both can run simultaneously if needed.

## Security Considerations

- The container runs with minimal privileges as a user service
- Sensitive information like passwords and API keys should be provided via files using the `*File` configuration options
- The container doesn't expose network ports unnecessarily, communicating via stdio with the MCP client