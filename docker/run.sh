#!/usr/bin/env bash
# Run a Python script inside the Isaac Sim 6.2.0 container, from the repo root.
#
#   docker/run.sh simulation/scripts/import_urdf.py
#   docker/run.sh simulation/scripts/check_robot_usd.py
#   docker/run.sh --shell      # bash inside the container
#
# The container runs as UID 1234 and sees the repo read-only, except robot_description/usd,
# which this grants UID 1234 write access to via ACLs (needs: sudo apt install acl).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=(docker compose -f "$REPO/docker/compose.yaml")

if ! command -v setfacl >/dev/null; then
    echo "setfacl not found: sudo apt install acl" >&2
    exit 1
fi
# The repo is mounted read-only; only robot_description/usd is writable by the container.
# Grant UID 1234 access there only. New files inherit rwx for 1234 and for you.
OUT="$REPO/robot_description/usd"
mkdir -p "$OUT"
setfacl -R -m u:1234:rwX "$OUT"
find "$OUT" -type d -exec setfacl -d -m u:1234:rwx,u:"$(id -u)":rwx {} +

if [[ "${1:-}" == "--shell" ]]; then
    exec "${COMPOSE[@]}" run --rm --entrypoint bash isaac-sim
fi
if [[ $# -eq 0 ]]; then
    echo "usage: docker/run.sh <script.py> [args...] | --shell" >&2
    exit 2
fi
exec "${COMPOSE[@]}" run --rm isaac-sim "$@"
