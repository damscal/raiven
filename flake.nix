{
  description = "RAIVEN: Holographic Cognitive Memory System";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        raivenPackage = pkgs.stdenv.mkDerivation {
          pname = "raiven";
          version = "0.1.0";
          src = ./.;
          
          installPhase = ''
            mkdir -p $out/bin
            echo '#!/usr/bin/env bash' > $out/bin/raiven-mcp
            echo 'exec docker run --rm -i raiven-mcp:latest "$@"' >> $out/bin/raiven-mcp
            chmod +x $out/bin/raiven-mcp
          '';
          
          buildPhase = "true";
          configurePhase = "true";
          
          meta = {
            description = "Holographic Cognitive Memory System (thin client)";
            license = "mit";
          };
        };
      in
      {
        apps.default = {
          type = "app";
          program = "${raivenPackage}/bin/raiven-mcp";
          meta = {
            description = "RAIVEN MCP client";
          };
        };

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [ python311 docker ];
        };
        
        packages.raiven-docker-image = pkgs.dockerTools.buildImage {
          name = "raiven-mcp";
          tag = "latest";
          copyToRoot = [ pkgs.dockerTools.caCertificates ];
          config = {
            Cmd = [ "/bin/sh" "-c" "echo 'raiven-mcp container ready'" ];
            Env = [ "PYTHONUNBUFFERED=1" ];
          };
        };
        
        packages.default = raivenPackage;
      }) // {
        homeManagerModules.default = import ./hm-module.nix;
      };
}