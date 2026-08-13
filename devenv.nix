{
  config,
  inputs,
  lib,
  pkgs,
  ...
}: {
  imports = [
    ./_meta/nix/git-hooks.nix
    ./_meta/nix/scripts.nix
    ./_meta/nix/tasks.nix
    ./_meta/nix/treefmt.nix
  ];

  packages = [
    pkgs.alejandra
    pkgs.biome
    pkgs.cspell
    pkgs.findutils
    pkgs.gawk
    pkgs.git
    pkgs.gnugrep
    pkgs.gnused
    pkgs.nixd
    pkgs.uv
  ];

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

    python.enable = true;
    python.venv.enable = true;
    python.version = "3.14";

    python.uv = {
      enable = true;
      sync.enable = true;
      sync.allExtras = true; # All optional dependencies
      sync.allGroups = false; # All dependency groups
      sync.allPackages = false; # All uv workspace members
    };
  };
}
