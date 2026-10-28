#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

EVIDENCE="bang-chung/m3/dependency/dependency-policy.txt"

{
  echo "Dependency Policy Evidence"
  echo "=========================="
  echo "tool=python3"
  python3 --version
  echo "checker=scripts/dependency_policy.py"
  echo "manifest=ma-nguon/order-app/requirements.txt"
  echo "policy=cau-hinh/m3/dependency-policy.yml"
  echo "command=python3 scripts/dependency_policy.py"
  echo "output=bang-chung/m3/dependency/dependency-policy.txt"
  echo
  python3 scripts/dependency_policy.py
} | tee "$EVIDENCE"
