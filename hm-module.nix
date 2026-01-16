{ config, lib, pkgs, ... }:

with lib;
with builtins;

let
  cfg = config.services.raiven;
  toEnvValue = v: if isPath v then toString v else v;
in {
  options.services.raiven = {
    enable = mkEnableOption "RAIVEN Holographic Cognitive Memory System";

    package = mkOption {
      type = types.package;
      description = "The RAIVEN package to use.";
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

      mcpClients = mkOption {
        type = types.listOf (types.enum ["roo-code" "cline" "vscode" "cursor"]);
        default = [];
        description = "List of MCP clients to automatically configure with the Raiven MCP server.";
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

    # One-shot service to build and load the Docker image during activation
    systemd.user.services.raiven-docker-setup = {
      Unit = {
        Description = "Build and load Raiven Docker image";
      };

      Service = {
        Type = "oneshot";
        ExecStart = pkgs.writeShellScript "raiven-docker-setup" ''
          set -e

          echo "Building Raiven MCP Docker image..."
          # Always build the latest Docker image
          nix build "${cfg.package.src}#raiven-docker-image" --out-link /tmp/raiven-docker-result

          echo "Loading Raiven MCP image into container runtime..."
          # Try podman first, then docker
          if command -v podman >/dev/null 2>&1; then
            # Remove old image if it exists
            podman rmi raiven-mcp:latest 2>/dev/null || true
            podman load < /tmp/raiven-docker-result
            echo "Loaded image into podman"
          elif command -v docker >/dev/null 2>&1; then
            # Remove old image if it exists
            docker rmi raiven-mcp:latest 2>/dev/null || true
            docker load < /tmp/raiven-docker-result
            echo "Loaded image into docker"
          else
            echo "Neither podman nor docker found, cannot load image"
            exit 1
          fi

          # Clean up
          rm -f /tmp/raiven-docker-result
          echo "Raiven MCP Docker setup complete"
        '';
        RemainAfterExit = true;
      };

      Install = {
        WantedBy = [ "default.target" ];
      };
    };

    # Periodic cleanup service for orphaned containers
    systemd.user.services.raiven-container-cleanup = {
      Unit = {
        Description = "Clean up orphaned Raiven MCP containers";
      };

      Service = {
        Type = "oneshot";
        ExecStart = pkgs.writeShellScript "raiven-container-cleanup" ''
          echo "Cleaning up orphaned Raiven MCP containers..."

          # Clean up podman containers
          if command -v podman >/dev/null 2>&1; then
            # Remove exited containers from raiven-mcp image
            podman rm $(podman ps -a -q --filter ancestor=localhost/raiven-mcp:latest --filter status=exited 2>/dev/null) 2>/dev/null || true
            # Remove containers that have been running for more than 1 hour (likely orphaned)
            podman rm $(podman ps -a -q --filter ancestor=localhost/raiven-mcp:latest --filter "status=running" --format "{{.ID}} {{.Created}}" | awk '$2 < "'$(date -d '1 hour ago' +%s)'" {print $1}' 2>/dev/null) 2>/dev/null || true
          fi

          # Clean up docker containers
          if command -v docker >/dev/null 2>&1; then
            # Remove exited containers from raiven-mcp image
            docker rm $(docker ps -a -q --filter ancestor=localhost/raiven-mcp:latest --filter status=exited 2>/dev/null) 2>/dev/null || true
            # Remove containers that have been running for more than 1 hour (likely orphaned)
            docker rm $(docker ps -a -q --filter ancestor=localhost/raiven-mcp:latest --filter "status=running" --format "{{.ID}} {{.CreatedAt}}" | awk '$2 < "'$(date -d '1 hour ago' +%s)'" {print $1}' 2>/dev/null) 2>/dev/null || true
          fi

          echo "Raiven MCP container cleanup complete"
        '';
      };
    };

    # Timer to run cleanup periodically
    systemd.user.timers.raiven-container-cleanup = {
      Unit = {
        Description = "Run Raiven MCP container cleanup periodically";
      };

      Timer = {
        OnBootSec = "5min";
        OnUnitActiveSec = "30min";
        Persistent = true;
      };

      Install = {
        WantedBy = [ "timers.target" ];
      };
    };

    # MCP client configuration
    home.activation = mkMerge (map (client:
      let
        configDir = {
          "roo-code" = ".config/VSCodium/User/globalStorage/rooveterinaryinc.roo-cline";
          "cline" = ".config/VSCodium/User/globalStorage/saoudrizwan.claude-dev";
          "vscode" = ".config/Code/User/globalStorage/rooveterinaryinc.roo-cline";
          "cursor" = ".config/cursor";
        }.${client} or (throw "Unsupported MCP client: ${client}");

        raivenConfig = {
          command = "podman";
          args = [
            "run"
            "-i"
            "--rm"
            "-v" "${config.home.homeDirectory}/.config/sops-nix/secrets:/secrets:ro"
            "-e" "RAIVEN_NEO4J_URI=${cfg.config.neo4j.uri}"
            "-e" "RAIVEN_NEO4J_USER=${cfg.config.neo4j.user}"
            "-e" "RAIVEN_NEO4J_PASSWORD_FILE=/secrets/server1os1-neo4j-password"
            "-e" "RAIVEN_NEO4J_API_KEY_FILE=/secrets/server1os1-neo4j-api-key"
            "-e" "RAIVEN_OLLAMA_HOST=${cfg.config.ollama.host}"
            "-e" "RAIVEN_OLLAMA_API_KEY_FILE=/secrets/server1os1-ollama-api-key"
            "-e" "RAIVEN_OLLAMA_MODEL=${cfg.config.ollama.model.name}"
            "localhost/raiven-mcp:latest"
          ];
          env = {
            "RAIVEN_VECTOR_DIMENSIONS" = toString cfg.config.ollama.model.vectorDimensions;
          };
          disabled = false;
          alwaysAllow = [];
          disabledTools = [];
        };
      in {
        "raiven-mcp-${client}" = lib.hm.dag.entryAfter ["writeBoundary"] ''
          $DRY_RUN_CMD mkdir -p "${config.home.homeDirectory}/${configDir}/settings"
          $DRY_RUN_CMD cat > "${config.home.homeDirectory}/${configDir}/raiven-config.json" << EOF
          ${builtins.toJSON raivenConfig}
          EOF
          if [ -f "${config.home.homeDirectory}/${configDir}/settings/mcp_settings.json" ]; then
            $DRY_RUN_CMD ${pkgs.jq}/bin/jq --slurpfile raiven "${config.home.homeDirectory}/${configDir}/raiven-config.json" \
              '.mcpServers.raiven = $raiven[0]' \
              "${config.home.homeDirectory}/${configDir}/settings/mcp_settings.json" > "${config.home.homeDirectory}/${configDir}/settings/mcp_settings.json.tmp"
          else
            # If the file doesn't exist, create it with just the raiven config
            $DRY_RUN_CMD ${pkgs.jq}/bin/jq --slurpfile raiven "${config.home.homeDirectory}/${configDir}/raiven-config.json" \
              '{mcpServers: {raiven: $raiven[0]}}' > "${config.home.homeDirectory}/${configDir}/settings/mcp_settings.json.tmp"
          fi
          $DRY_RUN_CMD mv "${config.home.homeDirectory}/${configDir}/settings/mcp_settings.json.tmp" "${config.home.homeDirectory}/${configDir}/settings/mcp_settings.json"
          $DRY_RUN_CMD rm -f "${config.home.homeDirectory}/${configDir}/raiven-config.json"
        '';
      }
    ) cfg.config.mcpClients);

  };
}
