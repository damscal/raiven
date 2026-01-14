{
  description = "RAIVEN: Holographic Cognitive Memory System";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        # Optimize for low-end systems by reducing parallel builds and memory usage
        # This configuration helps prevent build failures on systems with limited resources
        pkgs = import nixpkgs {
          inherit system;
          config = {
            allowUnfree = true;
            # Reduce parallel builds to prevent overwhelming low-end systems
            allowImportFromDerivation = true;
          };
          overlays = [];
        };
        python = pkgs.python311;
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python311;
        pythonPackages = pkgs.python311Packages.override {
          overrides = self: super: {
            # Disable tests to speed up rebuilds
            watchfiles = super.watchfiles.overridePythonAttrs (oldAttrs: {
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
            
            setuptools = super.setuptools.overridePythonAttrs (oldAttrs: {
              doCheck = false;
            });
            
            curio = super.curio.overridePythonAttrs (oldAttrs: {
              doCheck = false;
            });
          };
        };
        
        raivenPackage = pythonPackages.buildPythonApplication {
          pname = "raiven";
          version = "0.1.0";
          src = ./.;
          format = "pyproject";
          
          # Optimize build for faster rebuilds on low-end systems
          # Only run essential checks
          doCheck = false;
          doInstallCheck = false;
          
          # Additional optimizations for low-resource builds
          # Reduce optimization level to decrease build time
          pythonImportsCheck = [ ];

          # Dependency management:
          # We use the packages provided by nixpkgs to ensure compatibility
          propagatedBuildInputs = [
            pythonPackages.neo4j
            pythonPackages.requests
            pythonPackages.numpy
            pythonPackages.setuptools
            pythonPackages.mcp
            pythonPackages.curio
          ];

          # Disable tests if they require remote services or complex setup
          doCheck = false;

          # Additional optimizations for low-end systems
          nativeBuildInputs = with pkgs; [
            python311Packages.setuptools
          ];
          
          # Reduce parallel builds to avoid overwhelming low-end systems
          enableParallelBuilding = true;
          
          # Additional build optimizations for low-end systems
          # Skip byte-compilation optimization to save build time
          pythonBytecodeCompile = false;
          
          meta = with pkgs.lib; {
            description = "Holographic Cognitive Memory System";
            license = licenses.mit;
            maintainers = [ ];
            platforms = platforms.all;
          };
        };
        
        # Create a Python environment with raiven and all its optimized dependencies
        raivenPythonEnv = pythonPackages.withPackages (ps: [
          raivenPackage
          ps.requests
          ps.neo4j
          ps.numpy
          ps.mcp
          ps.curio
        ]);
      in
      {
        apps.default = {
          type = "app";
          program = "${self.packages.${system}.raiven-docker-image}/bin/raiven";
        };

        devShells.default = pkgs.mkShell {
          buildInputs = [
            (pythonPackages.withPackages (ps: with ps; [
              ps.neo4j
              ps.requests
              ps.numpy
              ps.setuptools
              ps.curio
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
