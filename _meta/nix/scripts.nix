{
  pkgs,
  lib,
  inputs,
  config,
  ...
}: {
  scripts = {
    _link_binaries_to_workspace = {
      exec = ''
        set -eu

        treefmtBin="${lib.getExe pkgs.treefmt}"
        treefmtCfg="${config.treefmt.config.build.configFile}"
        biomeBin="${lib.getExe pkgs.biome}"

        wspRoot="''${WORKSPACE_ROOT:-"''${DEVENV_ROOT:-"."}"}"
        if mkdir -p "$wspRoot/_meta/bin"; then
          [ -f "$treefmtBin" ] && ln -sf "$treefmtBin" "$wspRoot/_meta/bin/treefmt"
          [ -f "$treefmtCfg" ] && ln -sf "$treefmtCfg" "$wspRoot/_meta/config/treefmt.toml"
          [ -f "$biomeBin" ]   && ln -sf "$biomeBin"   "$wspRoot/_meta/bin/biome"
        fi
      '';
    };

    git = {
      exec = ''
        UTC_TIMESTAMP="$(date '+%s')+0000"
        export TZ="UTC" GIT_AUTHOR_DATE="$UTC_TIMESTAMP" GIT_COMMITTER_DATE="$UTC_TIMESTAMP"
        "${lib.getExe pkgs.git}" "$@"
      '';
    };

    git-hooks-install = {
      exec = ''
        prek -f --install-hooks
        prek -f --hook-type pre-commit --hook-type pre-push --hook-type commit-msg
      '';
    };

    git-hooks-fix = {
      exec = ''
        git config --unset-all core.hooksPath 2>/dev/null
        prek -f --install-hooks 2>/dev/null
        prek -f --hook-type pre-commit --hook-type pre-push --hook-type commit-msg 2>/dev/null
      '';
    };
  };
}
