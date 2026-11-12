#!/usr/bin/env bash
# Vendor the Apache Tomcat release-signing keys into the repo (provenance).
# Review the diff + verify fingerprints against https://tomcat.apache.org/download-<major>.cgi
# before committing. Never fetch keys at build time.
set -euo pipefail
cd "$(dirname "$0")"
for m in 9 10 11; do
  curl -fsSL "https://downloads.apache.org/tomcat/tomcat-$m/KEYS" -o "keys/KEYS-tomcat-$m"
done
echo "Done - review and commit keys/."
