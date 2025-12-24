{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.raiven;
in {
  options.services.raiven = {
    enable = mkEnableOption "RAIVEN Holographic Cognitive Memory System";

    package = mkOption {
      type = types.package;
      description = "The RAIVEN package to use.";
    };

    neo4j = {
      uri = mkOption {
        type = types.str;
        default = "https://server1os1.oneira.pp.ua/neo4j/";
        description = "Neo4j URI.";
      };
      user = mkOption {
        type = types.str;
        default = "neo4j";
        description = "Neo4j Username.";
      };
      passwordFile = mkOption {
        type = types.nullOr types.str;
        default = null;
        description = "Path to file containing Neo4j Password.";
      };
      apiKeyFile = mkOption {
        type = types.nullOr types.str;
        default = null;
        description = "Path to file containing Neo4j API Key.";
      };
    };

    ollama = {
      host = mkOption {
        type = types.str;
        default = "https://server1os1.oneira.pp.ua/ollama/";
        description = "Ollama Host URI.";
      };
      apiKeyFile = mkOption {
        type = types.nullOr types.str;
        default = null;
        description = "Path to file containing Ollama API Key.";
      };
      model = mkOption {
        type = types.str;
        default = "embeddinggemma:latest";
        description = "Ollama embedding model.";
      };
    };

    vectorDimensions = mkOption {
      type = types.int;
      default = 768;
      description = "Vector dimensions for the embedding model.";
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
          "RAIVEN_NEO4J_URI=${cfg.neo4j.uri}"
          "RAIVEN_NEO4J_USER=${cfg.neo4j.user}"
          "RAIVEN_OLLAMA_HOST=${cfg.ollama.host}"
          "RAIVEN_OLLAMA_MODEL=${cfg.ollama.model}"
          "RAIVEN_VECTOR_DIMENSIONS=${toString cfg.vectorDimensions}"
        ] 
        ++ (optional (cfg.neo4j.passwordFile != null) "RAIVEN_NEO4J_PASSWORD_FILE=${cfg.neo4j.passwordFile}")
        ++ (optional (cfg.neo4j.apiKeyFile != null) "RAIVEN_NEO4J_API_KEY_FILE=${cfg.neo4j.apiKeyFile}")
        ++ (optional (cfg.ollama.apiKeyFile != null) "RAIVEN_OLLAMA_API_KEY_FILE=${cfg.ollama.apiKeyFile}");
      };

      Install = {
        WantedBy = [ "default.target" ];
      };
    };
  };
}
