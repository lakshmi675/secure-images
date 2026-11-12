#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
img="$1"
chmod -R a+rX tests
cid=$(docker run -d -p 8080:8080 -v "$PWD/tests/ROOT:/opt/tomcat/webapps/ROOT:ro" "$img")
trap 'docker logs "$cid" 2>&1 | tail -40; docker rm -f "$cid" >/dev/null 2>&1 || true' EXIT
for _ in $(seq 1 40); do curl -fs localhost:8080/ >/dev/null 2>&1 && break; sleep 1; done
resp=$(curl -fsi localhost:8080/)
grep -q "tomcat-hardened-ok" <<<"$resp"                         || { echo "FAIL: app not served"; exit 1; }
if grep -qiE '^server:[[:space:]]*[^[:space:]]' <<<"$resp"; then echo "FAIL: Server header leaked"; exit 1; fi
if curl -s localhost:8080/nope | grep -qi "apache tomcat"; then echo "FAIL: version leaked on 404"; exit 1; fi
[ "$(docker inspect -f '{{.Config.User}}' "$img")" = "65532:65532" ] || { echo "FAIL: not non-root"; exit 1; }
if docker run --rm --entrypoint /bin/sh "$img" -c true >/dev/null 2>&1; then echo "FAIL: shell present"; exit 1; fi
echo "smoke test OK"
