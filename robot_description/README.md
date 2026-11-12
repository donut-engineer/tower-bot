# robot_description

SO-ARM101 robot model: `urdf/` source description, `meshes/` geometry, `usd/` converted assets for Isaac Sim.

## Source

Vendored from [TheRobotStudio/SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100) at commit
`a758567`, Apache-2.0. See [NOTICE](NOTICE) for the exact files and the one edit (mesh paths).

Variant: `so101_new_calib_camera.urdf`. This is the follower arm with the wrist camera mount. Its joint zeros match
the current LeRobot calibration.

| Joint | Type | Parent → child |
|---|---|---|
| `shoulder_pan` | revolute | `base_link` → `shoulder_link` |
| `shoulder_lift` | revolute | `shoulder_link` → `upper_arm_link` |
| `elbow_flex` | revolute | `upper_arm_link` → `lower_arm_link` |
| `wrist_flex` | revolute | `lower_arm_link` → `wrist_link` |
| `wrist_roll` | revolute | `wrist_link` → `gripper_link` |
| `gripper` | revolute | `gripper_link` → `moving_jaw_so101_v1_link` |

Fixed frames: `gripper_frame_link` (TCP), `wrist_camera_mount_link`, `wrist_camera_link`.

## Regenerating the USD

This uses the Isaac Sim 6.2.0 container ([`docker/`](../docker/)) on a Linux GPU host such as Brev. From the repo root:

```bash
docker/run.sh simulation/scripts/import_urdf.py      # writes into usd/ (prints the USD path)
docker/run.sh simulation/scripts/check_robot_usd.py  # headless sanity check
```

Generated USD: `usd/so101_new_calib_camera/so101_new_calib_camera.usda` (open this file). Physics is in a `Physics` variant set and defaults to `physx`.

Isaac Sim version used for the committed USD: **6.2.0** (`nvcr.io/nvidia/isaac-sim:6.2.0`, URDF importer 3.11.12). `check_robot_usd.py` passes on it.
