{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.raiven;
  toEnvValue = v: if isPath v then toString v else v;
in {
  options.services.raiven = {
    enable = mkEnableOption "RAIVEN Holographic Cognitive Memory System";

    enableContainerMCP = mkEnableOption "RAIVEN Containerized MCP Server";

    containerRuntime = mkOption {
      type = types.enum [ "podman" "docker" ];
      default = "podman";
      description = "Container runtime to use for the Raiven MCP server.";
    };

    package = mkOption {
      type = types.package;
      description = "The RAIVEN package to use.";
    };

    dockerImagePackage = mkOption {
      type = types.package;
      description = "The RAIVEN Docker image package to use for containerized MCP.";
    };

    config = {
      neo4j = {
        uri = mkOption {
          type = types.str;
          default = "";
          description = "Base Neo4j URI (Browser/Root).";
        };
        apiUrl = mkOption {
          type = types.nullOr types.str;
          default = null;
          description = "Explicit Neo4j REST API URI. If null, derived from uri.";
        };
        user = mkOption {
          type = types.str;
          default = "neo4j";
          description = "Neo4j Username.";
        };
        passwordFile = mkOption {
          type = types.nullOr (types.either types.str types.path);
          default = null;
          description = "Path to file containing Neo4j Password.";
        };
        apiKeyFile = mkOption {
          type = types.nullOr (types.either types.str types.path);
          default = null;
          description = "Path to file containing Neo4j API Key.";
        };
      };

      ollama = {
        host = mkOption {
          type = types.str;
          default = "";
          description = "Ollama Host URI.";
        };
        apiKeyFile = mkOption {
          type = types.nullOr (types.either types.str types.path);
          default = null;
          description = "Path to file containing Ollama API Key.";
        };
        model = {
          name = mkOption {
            type = types.str;
            default = "embeddinggemma:latest";
            description = "Ollama embedding model name.";
          };
          vectorDimensions = mkOption {
            type = types.int;
            default = 768;
            description = "Vector dimensions for the embedding model.";
          };
        };
      };
    };
  };

  config = mkIf cfg.enable {
    home.packages = [ cfg.package ];
    
    # Optimize nix settings for low-end systems
    nix = {
      settings = {
        # Limit parallel builds to prevent overwhelming low-end systems
        cores = 1;
        # Increase the timeout for builds on slower systems
        timeout = 3600;
        # Enable substituters for faster package acquisition
        "trusted-public-keys" = [
          "cache.nixos.org-1:6NCHdD59X431o0gWypbMrAURkbJ16ZPMQFGspcDShjY="
        ];
        "trusted-substituters" = [
          "https://cache.nixos.org/"
        ];
        # Allow fallback to binary caches to avoid building from source when possible
        "builders-use-substitutes" = true;  # Enable substituters on remote build machines when possible
        # Increase allowed size to prevent premature garbage collection
        "gc-reserved-space" = 1073741824; # 1GB reserved space
      };
    };

    systemd.user.services.raiven = {
      Unit = {
        Description = "RAIVEN Cognitive Memory Service";
        After = [ "network.target" ];
      };

      Service = {
        ExecStart = "${cfg.package}/bin/raiven";
        Restart = "on-failure";
        WorkingDirectory = "${config.home.homeDirectory}";
        Environment = [
          "PYTHONUNBUFFERED=1"
          "RAIVEN_NEO4J_URI=${cfg.config.neo4j.uri}"
          "RAIVEN_NEO4J_USER=${cfg.config.neo4j.user}"
          "RAIVEN_OLLAMA_HOST=${cfg.config.ollama.host}"
          "RAIVEN_OLLAMA_MODEL=${cfg.config.ollama.model.name}"
          "RAIVEN_VECTOR_DIMENSIONS=${toString cfg.config.ollama.model.vectorDimensions}"
        ] 
        ++ (optional (cfg.config.neo4j.apiUrl != null) "RAIVEN_NEO4J_API_URL=${cfg.config.neo4j.apiUrl}")
        ++ (optional (cfg.config.neo4j.passwordFile != null) "RAIVEN_NEO4J_PASSWORD_FILE=${toEnvValue cfg.config.neo4j.passwordFile}")
        ++ (optional (cfg.config.neo4j.apiKeyFile != null) "RAIVEN_NEO4J_API_KEY_FILE=${toEnvValue cfg.config.neo4j.apiKeyFile}")
        ++ (optional (cfg.config.ollama.apiKeyFile != null) "RAIVEN_OLLAMA_API_KEY_FILE=${toEnvValue cfg.config.ollama.apiKeyFile}");
      };

      Install = {
        WantedBy = [ "default.target" ];
      };
    };

    systemd.user.services.raiven-container-mcp = mkIf cfg.enableContainerMCP {
      Unit = {
        Description = "RAIVEN Containerized MCP Server";
        After = [ "network.target" ];
        Requires = [ "${cfg.containerRuntime}.socket" ];
      };

      Service = mkMerge [
        {
          Type = "exec";
          Restart = "on-failure";
          WorkingDirectory = "${config.home.homeDirectory}";
        }
        (mkIf (cfg.containerRuntime == "podman") {
          ExecStart = pkgs.writeShellScript "raiven-container-mcp-podman" ''
            # Load the pre-built Docker image into podman
            # Import the image from the nix store using the package's passthru
            if ! ${pkgs.podman}/bin/podman image exists raiven-mcp:latest; then
              echo "Loading raiven-mcp:latest image into podman..."
              ${pkgs.podman}/bin/podman load -i ${cfg.dockerImagePackage} > /dev/null 2>&1 || {
                echo "Failed to load Docker image"
                exit 1
              }
            fi
            
            # Run the container with proper stdio forwarding
            exec ${pkgs.podman}/bin/podman run -i --rm \
              --env-file ${pkgs.writeText "raiven-env" ''
                RAIVEN_NEO4J_URI=${cfg.config.neo4j.uri}
                RAIVEN_NEO4J_USER=${cfg.config.neo4j.user}
                RAIVEN_OLLAMA_HOST=${cfg.config.ollama.host}
                RAIVEN_OLLAMA_MODEL=${cfg.config.ollama.model.name}
                RAIVEN_VECTOR_DIMENSIONS=${toString cfg.config.ollama.model.vectorDimensions}
                ${optionalString (cfg.config.neo4j.apiUrl != null) "RAIVEN_NEO4J_API_URL=${cfg.config.neo4j.apiUrl}"}
                ${optionalString (cfg.config.neo4j.passwordFile != null) "RAIVEN_NEO4J_PASSWORD_FILE=${toEnvValue cfg.config.neo4j.passwordFile}"}
                ${optionalString (cfg.config.neo4j.apiKeyFile != null) "RAIVEN_NEO4J_API_KEY_FILE=${toEnvValue cfg.config.neo4j.apiKeyFile}"}
                ${optionalString (cfg.config.ollama.apiKeyFile != null) "RAIVEN_OLLAMA_API_KEY_FILE=${toEnvValue cfg.config.ollama.apiKeyFile}"}
              ''} \
              raiven-mcp
          '';
        })
        (mkIf (cfg.containerRuntime == "docker") {
          ExecStart = pkgs.writeShellScript "raiven-container-mcp-docker" ''
            # Load the pre-built Docker image if it doesn't exist
            if ! ${pkgs.docker}/bin/docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^raiven-mcp:latest$"; then
              echo "Loading raiven-mcp:latest image into docker..."
              ${pkgs.docker}/bin/docker load < ${cfg.dockerImagePackage} > /dev/null 2>&1 || {
                echo "Failed to load Docker image"
                exit 1
              }
            fi
            
            # Run the container with proper stdio forwarding
            exec ${pkgs.docker}/bin/docker run -i --rm \
              --env-file ${pkgs.writeText "raiven-env" ''
                RAIVEN_NEO4J_URI=${cfg.config.neo4j.uri}
                RAIVEN_NEO4J_USER=${cfg.config.neo4j.user}
                RAIVEN_OLLAMA_HOST=${cfg.config.ollama.host}
                RAIVEN_OLLAMA_MODEL=${cfg.config.ollama.model.name}
                RAIVEN_VECTOR_DIMENSIONS=${toString cfg.config.ollama.model.vectorDimensions}
                ${optionalString (cfg.config.neo4j.apiUrl != null) "RAIVEN_NEO4J_API_URL=${cfg.config.neo4j.apiUrl}"}
                ${optionalString (cfg.config.neo4j.passwordFile != null) "RAIVEN_NEO4J_PASSWORD_FILE=${toEnvValue cfg.config.neo4j.passwordFile}"}
                ${optionalString (cfg.config.neo4j.apiKeyFile != null) "RAIVEN_NEO4J_API_KEY_FILE=${toEnvValue cfg.config.neo4j.apiKeyFile}"}
                ${optionalString (cfg.config.ollama.apiKeyFile != null) "RAIVEN_OLLAMA_API_KEY_FILE=${toEnvValue cfg.config.ollama.apiKeyFile}"}
              ''} \
              raiven-mcp
          '';
        })
      ];

      Install = {
        WantedBy = [ "default.target" ];
      };
    };

  };
}
