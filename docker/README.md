# docker

Isaac Sim 6.2.0 (`nvcr.io/nvidia/isaac-sim:6.2.0`), headless, with the repo mounted at `/workspace`.

**Host:** native Linux with an RTX GPU, NVIDIA driver, Docker and the NVIDIA Container Toolkit. A Brev instance works.
WSL2 does not work, because Isaac Sim needs the NVIDIA Vulkan driver, which WSL2 doesn't provide.

```bash
sudo apt install acl                                   # once; run.sh uses setfacl
docker/run.sh simulation/scripts/import_urdf.py        # run a script with Isaac Sim's python
docker/run.sh --shell                                  # bash inside the container
```

- **First run:** the first run pulls about 20 GB and warms the shader caches. Caches are kept in named Docker volumes, so later runs are faster.
- **File access:** the container runs as UID 1234, the image's user, which isn't root. It sees the repo read-only. Only `robot_description/usd/` is writable, and `run.sh` grants UID 1234 write access there with ACLs. Anything else that needs writing gets its own mount.
- **Network:** no ports are published and there's no host networking. The future GUI/livestream service will need `network_mode: host`.
- **Privileges:** `no-new-privileges` is set and all Linux capabilities are dropped.
- **License:** `ACCEPT_EULA=Y` accepts NVIDIA's Isaac Sim license on your behalf.
- **Telemetry:** `PRIVACY_CONSENT` is not set, so you don't opt in to telemetry.
