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

      Service = {
        Type = "exec";
        ExecStart = pkgs.writeShellScript "raiven-container-mcp" ''
          CONTAINER_RUNTIME="${cfg.containerRuntime}"
          RUNTIME_CMD="${if cfg.containerRuntime == "podman" then pkgs.podman else pkgs.docker}/bin/${cfg.containerRuntime}"
          
          # Build the image if it doesn't exist
          if ! $RUNTIME_CMD images --format "{{.Repository}}:{{.Tag}}" | grep -q "^raiven-mcp:latest$"; then
            echo "Building raiven-mcp image with $CONTAINER_RUNTIME..."
            cd ${config.home.homeDirectory}/raiven && $RUNTIME_CMD build -t raiven-mcp .
          fi
          
          # Run the container with proper stdio forwarding
          exec $RUNTIME_CMD run -i --rm \
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
        Restart = "on-failure";
        WorkingDirectory = "${config.home.homeDirectory}";
      };

      Install = {
        WantedBy = [ "default.target" ];
      };
    };

  };
}
