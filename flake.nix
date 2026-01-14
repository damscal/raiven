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
        python = pkgs.python311;
        pythonPackages = pkgs.python311Packages.override {
          overrides = self: super: {
            watchfiles = super.watchfiles.overridePythonAttrs (old: {
              doCheck = false;
            });
          };
        };
        
        raivenPackage = pythonPackages.buildPythonApplication {
          pname = "raiven";
          version = "0.1.0";
          src = ./.;
          format = "pyproject";

          # Dependency management:
          # We use the packages provided by nixpkgs to ensure compatibility
          propagatedBuildInputs = [
            pythonPackages.neo4j
            pythonPackages.requests
            pythonPackages.numpy
            pythonPackages.setuptools
            pythonPackages.mcp
          ];

          # Disable tests if they require remote services or complex setup
          doCheck = false;

          meta = with pkgs.lib; {
            description = "Holographic Cognitive Memory System";
            license = licenses.mit;
            maintainers = [ ];
            platforms = platforms.all;
          };
        };
      in
      {
        apps.default = {
          type = "app";
          program = "${self.packages.${system}.raiven-docker-image}/bin/raiven";
        };

        devShells.default = pkgs.mkShell {
          buildInputs = [
            (python.withPackages (ps: with ps; [
              neo4j
              requests
              numpy
              setuptools
            ]))
          ];
        };
        
        packages.raiven-docker-image = pkgs.dockerTools.buildImage {
          name = "raiven-mcp";
          tag = "latest";
          
          contents = [
            pkgs.cacert
            pkgs.coreutils
            pkgs.bash
            pkgs.dockerTools.caCertificates
            pkgs.python311
          ];
          
          config = {
            Cmd = [
              "${pkgs.python311.interpreter}"
              "-c"
              "import sys; sys.path.insert(0, '${raivenPackage}/lib/python3.11/site-packages'); from raiven.raiven_mcp import main; main()"
            ];
            Env = [ "PYTHONUNBUFFERED=1" ];
          };
        };
        
        # Create the default package with Docker image in passthru
        packages.default = raivenPackage.overrideAttrs (oldAttrs: {
          passthru = (oldAttrs.passthru or {}) // {
            dockerImage = self.packages.${system}.raiven-docker-image;
          };
        });
      }) // {
        homeManagerModules.default = import ./hm-module.nix;
      };
}
