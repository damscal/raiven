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
        pythonPackages = pkgs.python311Packages;
      in
      {
        packages.default = pythonPackages.buildPythonApplication {
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

        apps.default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/raiven";
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
      }) // {
        homeManagerModules.default = import ./hm-module.nix;
      };
}
