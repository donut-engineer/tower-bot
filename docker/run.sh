#!/usr/bin/env bash
# Run a Python script inside the Isaac Sim 6.2.0 container, from the repo root.
#
#   docker/run.sh simulation/scripts/import_urdf.py
#   docker/run.sh simulation/scripts/check_robot_usd.py
#   docker/run.sh --shell      # bash inside the container
#
# The container runs as UID 1234, so this grants that UID write access to the repo
# via ACLs (needs the `acl` package: sudo apt install acl). Your own permissions are unchanged.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=(docker compose -f "$REPO/docker/compose.yaml")

if ! command -v setfacl >/dev/null; then
    echo "setfacl not found: sudo apt install acl" >&2
    exit 1
fi
# Existing files and dirs: rwX for 1234. New files: inherit rwx for 1234 and for you.
setfacl -R -m u:1234:rwX "$REPO"
find "$REPO" -type d -not -path '*/.git/*' -exec setfacl -d -m u:1234:rwx,u:"$(id -u)":rwx {} +

if [[ "${1:-}" == "--shell" ]]; then
    exec "${COMPOSE[@]}" run --rm --entrypoint bash isaac-sim
fi
if [[ $# -eq 0 ]]; then
    echo "usage: docker/run.sh <script.py> [args...] | --shell" >&2
    exit 2
fi
exec "${COMPOSE[@]}" run --rm isaac-sim "$@"
