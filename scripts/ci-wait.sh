#!/usr/bin/env bash
# Empuja HEAD y espera al workflow indicado (por defecto tests.yml) de ese commit.
# Sale con el código del run; si falla, imprime el log de los pasos fallidos.
set -u
workflow="${1:-tests.yml}"
git push -q origin HEAD || exit 1
sha="$(git rev-parse HEAD)"
id=""
for _ in $(seq 1 60); do
  id="$(gh run list --commit "$sha" --workflow "$workflow" --json databaseId -q '.[0].databaseId')"
  [ -n "$id" ] && break
  sleep 5
done
[ -n "$id" ] || { echo "no run of $workflow for $sha"; exit 2; }
gh run watch "$id" --exit-status > /dev/null
status=$?
[ "$status" -ne 0 ] && gh run view "$id" --log-failed | tail -n 80
echo "run $id: exit $status"
exit "$status"
