{
  lib,
  pkgs,
  ...
}: let
  wspRoot = ".";
  cfgDir = "_meta/config";
in {
  git-hooks = {
    enable = true;
    install.enable = true;
    package = pkgs.prek;

    default_stages = [
      "pre-commit"
      "pre-push"
      "commit-msg"
    ];

    excludes = [
      ".*-lock\..*"
      ".*\.lock$"
      ".*example.*"
      "cspell\.txt"
    ];

    hooks = {
      # -------------------------------- Hooks ---------------------------------
      actionlint.enable = true;
      cargo-check.enable = true;
      check-added-large-files.enable = true;
      check-case-conflicts.enable = true;
      check-merge-conflicts.enable = true;
      check-symlinks.enable = true;
      clippy.enable = true;
      cspell-msg.enable = true;
      cspell-wsp.enable = true;
      end-of-file-fixer.enable = true;
      mixed-line-endings.enable = true;
      pyright.enable = true;
      pytest.enable = true;
      treefmt.enable = true;
      trim-trailing-whitespace.enable = true;
      trufflehog.enable = true;

      # ------------------------------- Options --------------------------------
      check-added-large-files.args = ["--maxkb=8192"];
      mixed-line-endings.args = ["--fix=auto"];

      treefmt = {
        settings = {
          fail-on-change = false;
          no-cache = false;
        };
      };

      trufflehog = {
        stages = ["pre-commit" "pre-push"];
        args = [
          "git"
          "\"file://${wspRoot}\""
          "--since-commit"
          "HEAD"
          "--results=verified"
          "--fail"
          "--exclude-paths=\"${cfgDir}/trufflehog_exclude.txt\""
          "--detector-timeout=15s"
        ];
      };

      pyright = {
        stages = ["pre-push"];
        types = ["python"];
        args = ["--project" "${wspRoot}"];
      };

      cspell-wsp = {
        name = "check spelling: workspace files";
        entry = "${pkgs.cspell}/bin/cspell";
        language = "system";
        stages = ["pre-commit" "pre-push"];
        args = [
          "--config"
          "${wspRoot}/cspell.config.yml"
          "--no-summary"
          "--no-progress"
          "--no-must-find-files"
        ];
      };

      cspell-msg = {
        name = "check spelling: commit message";
        always_run = true;
        entry = "${pkgs.cspell}/bin/cspell";
        language = "system";
        stages = ["commit-msg"];
        args = [
          "--config"
          "${wspRoot}/cspell.config.yml"
          "--no-must-find-files"
          "--no-progress"
          "--no-summary"
          "--files"
          ".git/COMMIT_EDITMSG"
        ];
      };

      pytest = {
        name = "pytest";
        always_run = true;
        language = "system";
        pass_filenames = false;
        stages = ["pre-push"];
        types = ["python"];
        entry = ''
          sh -c '
          _pytest="${wspRoot}/.devenv/state/venv/bin/pytest"
          if [ ! -x "$_pytest" ]; then
            echo "Skipping - pytest not found."
          else
            _found="$("${pkgs.findutils}/bin/find" "${wspRoot}" \
              -path "*/.*/*"             -prune -o  \
              -path "*/data/*"           -prune -o  \
              -path "*/vendor/*"         -prune -o  \
              -path "*/node_modules/*"   -prune -o  \
              -path "*/target/debug/*"   -prune -o  \
              -path "*/target/release/*" -prune -o  \
              -iname "*test*.py" -print
            )"
            [ "$_found" != "" ] && "$_pytest"
          fi'
        '';
      };

      golangci-lint = {
        name = "golangci-lint";
        entry = "${lib.getExe pkgs.golangci-lint}";
        language = "system";
        pass_filenames = false;
        stages = ["pre-commit"];
        types = ["go"];
        args = [
          "run"
          "--config=${cfgDir}/.golangci.yml"
          "--timeout=5m"
          "--skip-dirs-re=^(vendor|build|dist|target|\..*|_.*)$"
        ];
      };
    };
  };
}
