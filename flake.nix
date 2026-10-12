{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    flake-parts.url = "github:hercules-ci/flake-parts";

    lumberjack-compiler = {
      url = "github:L-tips/lumberjack-compiler";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {

      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];

      perSystem =
        { pkgs, ... }:

        {
          devShells.default = pkgs.mkShell {
            nativeBuildInputs = with pkgs; [
              # Use the cargo version of swim
              swim
              verilator
              uv
              surfer
              iverilog

              pkgs.llvmPackages.clang-unwrapped
              pkgs.llvmPackages.lld

              python313

              lz4 # seems like this version of verilator is broken without it
            ];
          };
        };
    };
}
