{
  description = "Native Epson Printer Utility and USB maintenance for NixOS";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/718f670e845328e9c2cecdd832835712b2cbd065";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
      packagesFor = system: import ./nix/packages.nix { pkgs = nixpkgs.legacyPackages.${system}; };
    in {
      packages = forAllSystems packagesFor;
      apps = forAllSystems (system: let p = self.packages.${system}; in {
        default = { type = "app"; program = "${p.epson-printer-utility}/bin/epson-printer-utility"; };
        gui = self.apps.${system}.default;
        cli = { type = "app"; program = "${p.epson-printer-utility}/bin/epson-printer-cli"; };
        ecbd = { type = "app"; program = "${p.epson-backend}/bin/ecbd"; };
      });
      devShells = forAllSystems (system: let
        pkgs = nixpkgs.legacyPackages.${system};
        p = self.packages.${system};
      in { default = pkgs.mkShell {
        inputsFrom = [ p.epson-printer-utility p.epson-backend ];
        packages = [ pkgs.python3 pkgs.usbutils ];
      }; });
      checks = forAllSystems (system: let
        pkgs = nixpkgs.legacyPackages.${system};
        p = self.packages.${system};
      in {
        inherit (p) epson-printer-utility epson-backend;
        module = import ./tests/module.nix { inherit nixpkgs system; module = self.nixosModules.default; };
      });
      nixosModules.default = import ./nix/module.nix;
    };
}
