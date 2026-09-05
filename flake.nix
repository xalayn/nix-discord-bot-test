{
  description = "Hello-world Discord bot";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [
        "aarch64-linux"
        "x86_64-linux"
      ];

      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;

      packageFor = system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        pkgs.callPackage ./package.nix { };
    in
    {
      packages = forAllSystems (system: {
        default = packageFor system;
        hello-discord-bot = self.packages.${system}.default;
      });

      apps = forAllSystems (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/hello-discord-bot";
        };
      });
    };
}
