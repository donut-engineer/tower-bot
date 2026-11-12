# Brev instance setup

Everything a fresh Brev GPU instance needs before `docker/run.sh` works, plus the problems we
hit getting here. Update this whenever a deployment needs something new. The goal is to turn
it into one setup script, or a custom launchable, once the full pipeline passes.

Instance used: `g2-standard-8`, NVIDIA L4, Ubuntu 22.04, NVIDIA driver `595.91.07` (server branch).

## Setup steps (each new instance)

Run from WSL with the `!` prefix in Claude Code, or in your own terminal.

1. **Wait for the instance to be ready.** `brev ls` should show `RUNNING / COMPLETED / READY`.
2. **Refresh SSH config:** `brev refresh`. Run it *after* the instance is ready: if you run
   it while the instance is still deploying, you get a stale IP and SSH times out.
3. **Install `acl`** (`run.sh` uses `setfacl`):
   `sudo apt-get install -y acl`
4. **Install the NVIDIA graphics/Vulkan libraries.** The instance ships compute-only drivers
   (`libnvidia-compute-*-server`, no Vulkan). Isaac Sim needs Vulkan even headless. Install
   the `libnvidia-gl` package at the *exact* version of the installed compute package:
   ```bash
   V=$(dpkg-query -W -f='${Version}' libnvidia-compute-595-server)
   sudo apt-get update -q && sudo apt-get install -y libnvidia-gl-595-server="$V"
   ls /usr/share/vulkan/icd.d/nvidia_icd.json   # must exist
   ```
5. **Clone:** `git clone https://github.com/donut-engineer/tower-bot.git`
6. **First `docker/run.sh` run** pulls `nvcr.io/nvidia/isaac-sim:6.2.0` (~20 GB). The first run
   takes a while.

## Running

```bash
cd tower-bot
docker/run.sh simulation/scripts/import_urdf.py > /tmp/import.log 2>&1; echo "exit=$?"
grep -vE "OmniHub|\] startup" /tmp/import.log | tail -40
```
Isaac Sim's output is very long. Save it to a file, then look at the tail. Don't grep for
specific patterns: a narrow filter once hid the only error line.

## Problems hit and fixes

| Symptom | Cause | Fix |
|---|---|---|
| `ssh: connect to host <ip> port 22: Connection timed out` | `brev refresh` was run while the instance was deploying, so the IP was stale | Re-run `brev refresh` once ready (host becomes Brev's relay) |
| `vkCreateInstance failed ... ERROR_INCOMPATIBLE_DRIVER` | Compose passed only the CUDA driver capabilities | `NVIDIA_DRIVER_CAPABILITIES=all` in compose (PR #3) |
| Same error, and `/usr/share/vulkan/icd.d` is missing on the host | Host has a compute-only driver | Step 4 above |
| `Permission denied: /isaac-sim/.cache/warp` | Named Docker volumes were root-owned; the container runs as UID 1234 | Host cache dirs + ACLs (PR #3) |
| `setfacl: ... Operation not permitted` | Only a file's owner can change its ACLs; the container owns its output | Skip files you don't own (PR #4) |
| `find: ... Permission denied`, `run.sh` exits 1 silently | `find` descended into container-private folders | Prune folders you don't own (PR #5) |
| `ImportError: cannot import name '_urdf'` | Isaac Sim 6.x replaced the URDF importer API | `URDFImporterConfig` + `URDFImporter` (PR #3) |
| Script failed but the run exited 0 | Kit swallowed the exit code | Hard-exit non-zero on failure (PR #3) |
| Import "succeeds" but has 0 joints | Physics lives in a `Physics` variant set with no default selection | Import script selects `physx` (PR #6) |
| Output folder `so101_new_calib_camera_1/` | Importer won't overwrite; it adds a suffix | Import script removes old output first (PR #6) |

## Open issues

- **Vulkan still fails** inside the container (`ERROR_INCOMPATIBLE_DRIVER`) even after step 4.
  The URDF import and CUDA (Warp sees the L4) work without it. Rendering, the camera sensor and
  the GUI will need it.
