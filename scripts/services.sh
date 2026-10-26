#!/usr/bin/env bash
# Ten sam wybor projektu dla start, stop i destroy.
set -euo pipefail
action="${1:?Podaj start, stop lub destroy}"
export ENVIRONMENT="${2:?Podaj env-test, env-qa lub main}"
case "$ENVIRONMENT" in
  env-test) export POSTGRES_PORT=5444 ;;
  env-qa) export POSTGRES_PORT=5445 ;;
  main) export POSTGRES_PORT=5446 ;;
  *) echo "Nieznane srodowisko" >&2; exit 1 ;;
esac
project="remote-db-$ENVIRONMENT"
compose=(docker compose -f docker-compose-remote.yml -p "$project")
case "$action" in
  start)
    "${compose[@]}" up -d --build --wait --wait-timeout 180 postgis
    "${compose[@]}" run --rm --build python
    "${compose[@]}" run --rm --no-deps python python3 /app/verify.py
    ;;
  stop) "${compose[@]}" stop ;;
  destroy)
    if [[ "${CONFIRM_DESTROY:-}" != "$project" ]]; then
      echo "Aby usunac dane, ustaw CONFIRM_DESTROY=$project" >&2
      exit 1
    fi
    "${compose[@]}" down --volumes --remove-orphans
    ;;
  *) echo "Nieznana operacja" >&2; exit 1 ;;
esac
