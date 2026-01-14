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
            # Disable tests for packages that cause expensive checks during rebuilds
            watchfiles = super.watchfiles.overridePythonAttrs (old: {
              doCheck = false;
            });
            
            # Additional Python packages that might have expensive tests
            neo4j = super.neo4j.overridePythonAttrs (oldAttrs: {
              doCheck = false;
            });
            
            requests = super.requests.overridePythonAttrs (oldAttrs: {
              doCheck = false;
            });
            
            numpy = super.numpy.overridePythonAttrs (oldAttrs: {
              doCheck = false;
            });
            
            mcp = super.mcp.overridePythonAttrs (oldAttrs: {
              doCheck = false;
            });
            
            websockets = super.websockets.overridePythonAttrs (oldAttrs: {
              doCheck = false;
            });
            
            # Additional packages that might have expensive tests
            setuptools = super.setuptools.overridePythonAttrs (oldAttrs: {
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
        
        # Create a Python environment with raiven and all its dependencies
        raivenPythonEnv = pkgs.python311.withPackages (ps: [
          raivenPackage
          ps.requests
          ps.neo4j
          ps.numpy
          ps.mcp
        ]);
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
          
          copyToRoot = pkgs.buildEnv {
            name = "raiven-mcp-docker-root";
            paths = [
              pkgs.cacert
              pkgs.coreutils
              pkgs.bash
              pkgs.dockerTools.caCertificates
              raivenPackage  # This includes the executable
            ];
            pathsToLink = [ "/" ];
          };
          
          config = {
            Cmd = [
              "${raivenPackage}/bin/raiven-mcp"
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
