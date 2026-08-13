{
  lib,
  pkgs,
  config,
  ...
}: let
  cfgDir = "_meta/config";

  excludes = {
    css = [];
    go = ["**/vendor/*"];
    html = [];
    js = [];
    json = [];
    md = [];
    nix = [];
    py = [];
    sh = [];
    toml = [];
    yaml = ["*golangci.y*ml"];
    rust = [];
  };

  includes = {
    css = ["*.css"];
    go = ["*.go"];
    html = ["*.htm" "*.html"];
    js = ["*.js" "*.ts" "*.mjs" "*.mts" "*.cjs" "*.cts" "*.jsx" "*.tsx" "*.d.ts" "*.d.cts" "*.d.mts"];
    json = ["*.json" "*.jsonc" "*.sublime-keymap" "*.sublime-settings"];
    md = ["*.md"];
    nix = ["*.nix"];
    py = ["*.py" "*.pyi" "*.ipynb"];
    sh = ["*.sh" "*.zsh" "zsh*" ".zsh*" "*.bash" "bash*" ".bash*" "profile" ".profile" "*.env" "*.envrc"];
    toml = ["*.toml"];
    yaml = ["*.yml" "*.yaml"];
    rust = ["*.rs"];
  };
in {
  treefmt = {
    enable = true;
    config = {
      programs = {
        # -------------------------------- Nix ---------------------------------
        alejandra = {
          enable = true;
          excludes = excludes.nix;
          includes = includes.nix;
        };

        # --------------------------------- Go ---------------------------------
        gofumpt.enable = true;
        gofumpt.excludes = excludes.go;
        gofumpt.includes = includes.go;

        goimports.enable = true;
        goimports.excludes = excludes.go;
        goimports.includes = includes.go;

        golines = {
          enable = true;
          maxLength = 200;
          tabLength = 4;
          excludes = excludes.go;
          includes = includes.go;
        };

        # -------------------------------- Rust --------------------------------
        rustfmt.enable = true;
      };

      settings = {
        formatter = {
          # -------------------------- Shell Scripts ---------------------------
          shfmt = {
            priority = 0;
            command = lib.getExe pkgs.shfmt;
            excludes = excludes.sh;
            includes = includes.sh;
            options = ["-s" "-ci" "-i" "2" "--write"];
          };
          shellharden = {
            priority = 1;
            command = lib.getExe pkgs.bash;
            # WARNING: '--replace' will break scripts that depend on word splitting!
            # To address this, we check for a shellcheck comment disabling any of the
            # rules listed below, and if found, refuse to run shellharden on that file.
            #   SC2046 - Quote this to prevent word splitting.
            #   SC2068 - Double quote array expansions to avoid re-splitting elements.
            #   SC2086 - Double quote to prevent globbing and word splitting.
            #   SC2206 - Quote to prevent word splitting/globbing, or split robustly with mapfile or read -a.
            #   SC2207 - Prefer mapfile or read -a to split command output (or quote to avoid splitting).
            #   SC2231 - Quote expansions in this for loop glob to prevent word splitting, e.g. "${dir}"/*.txt.
            options = [
              "-euc"
              ''
                for fp in "$@"; do
                  if ! "${pkgs.gnugrep}/bin/grep" -Eiq "disable=.*SC(2046|2068|2086|2206|2207|2231)" "$fp"; then
                    "${lib.getExe pkgs.shellharden}" --replace "$fp"
                  fi
                done
              ''
              "--" # bash swallows the second argument when using -c
            ];
            excludes = excludes.sh ++ ["*.env" "*.envrc"];
            includes = includes.sh;
          };

          # ------------------------------ Python ------------------------------
          ruff-check = {
            priority = 0;
            command = lib.getExe pkgs.ruff;
            excludes = excludes.py;
            includes = includes.py;
            options = ["--config" "${cfgDir}/ruff.toml" "check" "--fix-only"];
          };
          #docformatter = {
          #  priority = 1;
          #  command = lib.getExe pkgs.python313Packages.docformatter;
          #  excludes = excludes.py;
          #  includes = lib.lists.filter (i: i != "*.ipynb") includes.py;
          #  options = ["--in-place" "--style" "numpy" "--wrap-descriptions" "120" "--wrap-summaries" "120"];
          #};
          ruff-format = {
            priority = 2;
            command = lib.getExe pkgs.ruff;
            excludes = excludes.py;
            includes = includes.py;
            options = ["--config" "${cfgDir}/ruff.toml" "format"];
          };

          # ----------------------------- Markdown -----------------------------
          prettier-md = {
            priority = 0;
            command = lib.getExe pkgs.prettier;
            excludes = excludes.md;
            includes = includes.md;
            options = ["--config" "${cfgDir}/.prettierrc.yml" "--write"];
          };
          markdownlint = {
            priority = 1;
            command = lib.getExe pkgs.markdownlint-cli2;
            excludes = excludes.md;
            includes = includes.md;
            options = ["--config" "${cfgDir}/.markdownlint.yml" "--fix"];
          };

          # ------------------------------- TOML -------------------------------
          taplo = {
            priority = 0;
            command = lib.getExe pkgs.taplo;
            excludes = excludes.toml;
            includes = includes.toml;
            options = ["format" "--config" "${cfgDir}/taplo.toml"];
          };

          # ------------------------------- YAML -------------------------------
          yamlfmt = {
            priority = 0;
            command = lib.getExe pkgs.yamlfmt;
            excludes = excludes.yaml;
            includes = includes.yaml;
            options = ["-conf" "${cfgDir}/yamlfmt.yml" "format"];
          };

          # --------------- JavaScript / TypeScript / JSON / CSS ---------------
          biome = {
            priority = 0;
            command = lib.getExe pkgs.bash;
            excludes = excludes.js ++ excludes.json ++ excludes.css;
            includes = includes.js ++ includes.json ++ includes.css;
            options = [
              "-euc"
              ''
                export WORKSPACE_ROOT="''${WORKSPACE_ROOT:-"${config.git.root}"}"
                cd "${config.git.root}" || exit

                _biome_cfg="''${WORKSPACE_ROOT:?}/biome.json"
                _rm_biome_cfg() { [ -f "''${_biome_cfg:?}" ] && rm -f "$_biome_cfg"; }

                trap '_rm_biome_cfg' EXIT
                echo '{ "root": true }' > "''${_biome_cfg:?}"

                for fp in "$@"; do
                  "${lib.getExe pkgs.biome}" check --write --no-errors-on-unmatched \
                    --config-path "_meta/config/biome.jsonc" "$fp"
                done
              ''
              "--"
            ];
          };

          # ------------------------------- HTML -------------------------------
          #html-tidy = {
          #  priority = 0;
          #  command = lib.getExe pkgs.html-tidy;
          #  excludes = excludes.html;
          #  includes = includes.html;
          #  options = ["-config" "${cfgDir}/html_tidy.txt"];
          #};
          prettier-html = {
            priority = 0;
            command = lib.getExe pkgs.prettier;
            excludes = excludes.html;
            includes = includes.html;
            options = ["--config" "${cfgDir}/.prettierrc.yml" "--write"];
          };
        };
      };
    };
  };
}
