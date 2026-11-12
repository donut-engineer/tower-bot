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
# Give UID 1234 access to everything under $1 that you own. Anything not yours (files and
# folders the container created) is pruned, not descended into: it's already the container's,
# you can't change its ACLs, and its folders may not be readable by you.
grant() {
    local me
    me="$(id -u)"
    find "$1" ! -user "$me" -prune -o -exec setfacl -m u:1234:rwX {} +
    find "$1" ! -user "$me" -prune -o -type d -exec setfacl -d -m u:1234:rwx,u:"$me":rwx {} +
}

# The repo is mounted read-only; only robot_description/usd is writable by the container.
# Grant UID 1234 access there only. New files inherit rwx for 1234 and for you.
OUT="$REPO/robot_description/usd"
mkdir -p "$OUT"
grant "$OUT"

# Isaac Sim caches, logs and config, kept on the host so they persist between runs.
export ISAAC_CACHE="${ISAAC_CACHE:-$HOME/docker/isaac-sim}"
for d in cache/main cache/computecache cache/kit logs config data pkg; do
    mkdir -p "$ISAAC_CACHE/$d"
done
grant "$ISAAC_CACHE"

if [[ "${1:-}" == "--shell" ]]; then
    exec "${COMPOSE[@]}" run --rm --entrypoint bash isaac-sim
fi
if [[ $# -eq 0 ]]; then
    echo "usage: docker/run.sh <script.py> [args...] | --shell" >&2
    exit 2
fi
exec "${COMPOSE[@]}" run --rm isaac-sim "$@"
