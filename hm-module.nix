{ config, lib, pkgs, ... }:

with lib;

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

  };
}
