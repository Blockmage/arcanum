#!/usr/bin/env bash

log_msg() {
  local level="" msg="" color=""

  : "${LOG_NAME:="scripts"}"
  : "${LOG_DIR:="$WORKSPACE_ROOT/_meta/log"}"
  : "${LOG_FILE:="$LOG_DIR/${LOG_NAME%.*}.log"}"
  : "${LOG_STDOUT:=0}"
  : "${LOG_NO_TIMESTAMP:=}"

  level="$(printf '%.3s' "$1" | tr '[:upper:]' '[:lower:]')"

  case "$level" in
    8* | f | fat) shift 1 && level=" FATAL    " color="\e[40;91m" msg="$*" ;; # bright red
    7* | x | eme) shift 1 && level=" EMERG    " color="\e[40;91m" msg="$*" ;; # bright red
    6* | a | ale) shift 1 && level=" ALERT    " color="\e[40;91m" msg="$*" ;; # bright red
    5* | c | cri) shift 1 && level=" CRITICAL " color="\e[40;91m" msg="$*" ;; # red
    4* | e | err) shift 1 && level=" ERROR    " color="\e[40;31m" msg="$*" ;; # red
    3* | w | war) shift 1 && level=" WARNING  " color="\e[40;93m" msg="$*" ;; # bright yellow
    2* | n | not) shift 1 && level=" NOTICE   " color="\e[40;33m" msg="$*" ;; # yellow
    1* | i | inf) shift 1 && level=" INFO     " color="\e[40;97m" msg="$*" ;; # bright white
    01 | d | deb) shift 1 && level=" DEBUG    " color="\e[40;96m" msg="$*" ;; # bright cyan
    02 | t | tra) shift 1 && level=" TRACE    " color="\e[40;35m" msg="$*" ;; # magenta
    s | ok | suc) shift 1 && level=" SUCCESS  " color="\e[40;92m" msg="$*" ;; # bright green
    *) level=" INFO     " color="\e[40;97m" msg="$*" ;;
  esac

  case "$level" in
    *DEBU*) [ "${DEBUG:=0}" -ge 1 ] || return ;;
    *TRAC*) [ "${DEBUG:=0}" -ge 2 ] || return ;;
  esac

  if [ "${msg:-}" != "" ]; then
    local dr="" color_msg="" timestamp=""

    [ "${NO_COLOR:-}" != "" ] && color=""
    [ "${DRY_RUN:=0}" = "1" ] && dr="| DRY RUN "
    [ "${LOG_NO_TIMESTAMP:=}" = "" ] && timestamp="$(date -u -- '+%Y-%m-%dT%H:%M:%S%z') "

    if [ "${LOG_FILE:-}" != "" ] && [ ! -e "$LOG_FILE" ]; then
      mkdir -p -- "$(dirname -- "$LOG_FILE")" && touch -- "$LOG_FILE"
    fi

    color_msg="${timestamp:-}|${color:-}${level:-}\e[0m${dr:-}| ${msg}"
    msg="${timestamp:-}|${level:-}${dr:-}| ${msg}"

    [ -e "${LOG_FILE:-}" ] && printf -- '%b\n' "$msg" >>"$LOG_FILE"
    [ "${LOG_STDOUT:=0}" = "0" ] && printf -- '%b\n' "$color_msg" >&2
  fi

  return 0
}
