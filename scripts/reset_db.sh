#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../backend"
rm -f rewards.db
echo "Reset done."
