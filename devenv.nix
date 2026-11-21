{
  config,
  inputs,
  lib,
  pkgs,
  ...
}: let
  pkgs-u = import inputs.nixpkgs-unstable {system = pkgs.stdenv.system;};
in {
  imports = [
    ./_meta/nix/git-hooks.nix
    ./_meta/nix/scripts.nix
    ./_meta/nix/tasks.nix
    ./_meta/nix/treefmt.nix
  ];

  packages = [
    pkgs-u.git
    pkgs-u.go-tools
    pkgs-u.go_1_26
    pkgs-u.golangci-lint
    pkgs-u.nodejs_26
    pkgs-u.pnpm_12
    pkgs-u.uv

    pkgs.alejandra
    pkgs.biome
    pkgs.cspell

    pkgs.findutils
    pkgs.gawk
    pkgs.gnugrep
    pkgs.gnused

    pkgs.maturin

    pkgs.nixd
  ];

  dotenv.disableHint = true;

  env = {
    PYTHONPYCACHEPREFIX = ".pycache"; # Tidiness: Put bytecode files in a single folder.
    UV_EXCLUDE_NEWER = "14 days"; # Security: 14-day quarantine for uv-installed Python packages.
    PIP_UPLOADED_PRIOR_TO = "P14D"; # Security: 14-day quarantine for pip-installed Python packages.
    PIP_ONLY_BINARY = ":all:"; # Security: Block setup.py code execution at install time.

    NODE_OPTIONS = "--max-old-space-size=8096";

    NPM_CONFIG_AUDIT = "true";
    NPM_CONFIG_FUND = "false";
    NPM_CONFIG_IGNORE_SCRIPTS = "true";
    NPM_CONFIG_MINIMUM_RELEASE_AGE = "1440"; # Does this work? (Unable to find any documentation.)
    NPM_CONFIG_SAVE_EXACT = "true";
    NPM_CONFIG_UPDATE_NOTIFIER = "false";
  };

  enterShell = ''
    _link_binaries_to_workspace

    if [ -f "$DEVENV_STATE/venv/bin/activate" ]; then
      source "$DEVENV_STATE/venv/bin/activate"
    fi
  '';

  languages = {
    shell.enable = true;

    nix.enable = true;
    nix.lsp.package = pkgs.nixd; # pkgs.nil;

    python.enable = false;
    python.package = pkgs-u.python313;
    python.venv.enable = true;
    python.uv.enable = true;
    python.uv.package = pkgs-u.uv;
    python.uv.sync.allExtras = true;
    python.uv.sync.allGroups = true;
    python.uv.sync.allPackages = false;
    python.uv.sync.enable = true;

    go.enable = false;
    go.package = pkgs-u.go_1_26;
    go.delve.enable = true;
    go.delve.package = pkgs-u.delve;
    go.enableHardeningWorkaround = true; # Required for delve (https://github.com/go-delve/delve/issues/3085)

    javascript.enable = false;
    javascript.package = pkgs-u.nodejs_26;
    javascript.pnpm.enable = true;
    javascript.pnpm.package = pkgs-u.pnpm_12;
    javascript.pnpm.install.enable = false; # Whether to run `pnpm install` automatically

    typescript.enable = false;

    rust.enable = false;
    rust.version = "latest";
    rust.channel = "stable";
    rust.lld.enable = pkgs.stdenv.isDarwin;
    rust.mold.enable = pkgs.stdenv.isLinux;
    rust.components = ["rustc" "cargo" "clippy" "rustfmt" "rust-analyzer"];
    rust.targets = [
      "x86_64-unknown-linux-gnu"
      "aarch64-unknown-linux-gnu"
      "aarch64-apple-darwin"
    ];

    solidity.enable = false;
    solidity.foundry.enable = true;
  };
}
