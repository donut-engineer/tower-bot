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
- **File access:** the container runs as UID 1234, the image's user. `run.sh` uses ACLs to give that UID write access to the repo, so generated files such as `robot_description/usd/` land in your checkout.
- **Telemetry:** `PRIVACY_CONSENT` is not set, so you don't opt in to telemetry.
