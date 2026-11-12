"""Headless sanity check of the converted SO-ARM101 USD.

Run from the repo root with Isaac Sim's python, after import_urdf.py:
    docker/run.sh simulation/scripts/check_robot_usd.py

Checks: 6 expected DOFs, joint limits match the URDF, fixed base, stable rest pose,
position targets are tracked. Exits non-zero on any failure.
Targets Isaac Sim 6.2.0 (docker/compose.yaml). Uses `isaacsim.core.api`, which is deprecated
in 6.x but still shipped; move to `isaacsim.core.experimental` later.
"""

import argparse
import math
import os
import glob
import sys
import traceback
import xml.etree.ElementTree as ET

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--usd", default=os.path.join(REPO, "robot_description/usd"),
                    help="USD file, or a directory holding exactly one robot USD")
parser.add_argument("--urdf", default=os.path.join(REPO, "robot_description/urdf/so101_new_calib_camera.urdf"))
args = parser.parse_args()

from isaacsim import SimulationApp  # noqa: E402

app = SimulationApp({"headless": True})

import numpy as np  # noqa: E402
import omni.usd  # noqa: E402
from isaacsim.core.api import World  # noqa: E402
from isaacsim.core.prims import SingleArticulation, SingleXFormPrim  # noqa: E402
from isaacsim.core.utils.stage import add_reference_to_stage  # noqa: E402
from isaacsim.core.utils.types import ArticulationAction  # noqa: E402
from pxr import UsdPhysics  # noqa: E402

ROBOT_PATH = "/World/so101"
failures = []


def check(cond, msg):
    print(("  PASS " if cond else "  FAIL ") + msg)
    if not cond:
        failures.append(msg)


def urdf_limits(path):
    """{joint_name: (lower_rad, upper_rad)} for revolute joints."""
    root = ET.parse(path).getroot()
    out = {}
    for j in root.findall("joint"):
        if j.get("type") == "revolute":
            lim = j.find("limit")
            out[j.get("name")] = (float(lim.get("lower")), float(lim.get("upper")))
    return out


def find_prim(stage, under, pred):
    for prim in stage.Traverse():
        if str(prim.GetPath()).startswith(under) and pred(prim):
            return prim
    return None


def resolve_usd(path):
    if os.path.isfile(path):
        return path
    # Top-level file, or the importer's asset folder layout: <dir>/<name>/<name>.usd
    found = sorted(
        glob.glob(os.path.join(path, "*.usd")) + glob.glob(os.path.join(path, "*.usda"))
        + [f for f in glob.glob(os.path.join(path, "*", "*.usd*"))
           if os.path.splitext(os.path.basename(f))[0] == os.path.basename(os.path.dirname(f))]
    )
    if len(found) != 1:
        raise SystemExit(f"[check] expected one .usd in {path}, found {found}; pass --usd <file>")
    return found[0]


def main():
    expected = urdf_limits(args.urdf)
    usd = resolve_usd(os.path.abspath(args.usd))
    print("usd:", usd)

    world = World(stage_units_in_meters=1.0, physics_dt=1.0 / 120.0)
    world.scene.add_default_ground_plane()
    add_reference_to_stage(usd, ROBOT_PATH)
    stage = omni.usd.get_context().get_stage()

    root = find_prim(stage, ROBOT_PATH, lambda p: p.HasAPI(UsdPhysics.ArticulationRootAPI))
    if root is None:
        print("FAIL no ArticulationRootAPI prim found under", ROBOT_PATH)
        return 1
    print("articulation root:", root.GetPath())

    print("[limits: USD joints vs URDF]")
    for name, (lo, hi) in expected.items():
        jp = find_prim(stage, ROBOT_PATH, lambda p, n=name: p.GetName() == n and p.IsA(UsdPhysics.RevoluteJoint))
        if jp is None:
            check(False, f"joint prim '{name}' exists")
            continue
        j = UsdPhysics.RevoluteJoint(jp)
        ulo, uhi = j.GetLowerLimitAttr().Get(), j.GetUpperLimitAttr().Get()  # degrees
        check(
            math.isclose(ulo, math.degrees(lo), abs_tol=0.01) and math.isclose(uhi, math.degrees(hi), abs_tol=0.01),
            f"{name} limits [{ulo:.2f}, {uhi:.2f}] deg",
        )

    robot = world.scene.add(SingleArticulation(prim_path=str(root.GetPath()), name="so101"))
    world.reset()

    print("[dofs]")
    print("  order:", robot.dof_names)
    check(sorted(robot.dof_names) == sorted(expected), f"{robot.num_dof} DOFs match URDF revolute joints")

    print("[rest: 200 steps at zero targets]")
    robot.apply_action(ArticulationAction(joint_positions=np.zeros(robot.num_dof)))
    world.step(render=False)  # measure after physics has run once, not straight after reset
    base_before = np.array(robot.get_world_pose()[0], dtype=float)
    for _ in range(200):
        world.step(render=False)
    base_after = np.array(robot.get_world_pose()[0], dtype=float)
    q, qd = robot.get_joint_positions(), robot.get_joint_velocities()
    check(np.all(np.isfinite(q)) and np.all(np.isfinite(qd)), "joint state finite")
    drift = np.linalg.norm(base_after - base_before)
    print(f"  base pos before={np.round(base_before, 5)} after={np.round(base_after, 5)}")
    check(drift < 1e-3, f"base stays fixed (moved {drift * 1000:.3f} mm)")
    check(np.max(np.abs(qd)) < 0.05, f"settled (max |qd| = {np.max(np.abs(qd)):.4f} rad/s)")

    print("[tracking: shoulder_lift=0.5, elbow_flex=-0.5]")
    target = np.zeros(robot.num_dof)
    target[robot.get_dof_index("shoulder_lift")] = 0.5
    target[robot.get_dof_index("elbow_flex")] = -0.5
    robot.apply_action(ArticulationAction(joint_positions=target))
    for _ in range(360):
        world.step(render=False)
    err = np.abs(robot.get_joint_positions() - target)
    for name, e in zip(robot.dof_names, err):
        print(f"  {name:14s} err {e:.4f} rad")
    check(np.max(err) < 0.05, f"targets reached (max err {np.max(err):.4f} rad)")

    tcp = find_prim(stage, ROBOT_PATH, lambda p: p.GetName() == "gripper_frame_link")
    if tcp is not None:
        pos, quat = SingleXFormPrim(str(tcp.GetPath())).get_world_pose()
        print(f"[tcp] gripper_frame_link pos={np.round(pos, 4)} quat(wxyz)={np.round(quat, 4)}")
    else:
        check(False, "gripper_frame_link prim exists")

    print("\nRESULT:", "OK" if not failures else f"{len(failures)} failure(s)")
    return 0 if not failures else 1


if __name__ == "__main__":
    try:
        rc = main()
    except SystemExit as e:
        print(e)
        rc = 1
    except Exception:
        traceback.print_exc()
        rc = 1
    print(f"[check] exit {rc}", flush=True)
    sys.stderr.flush()
    if rc != 0:
        # Kit swallowed the exit code on the first run (failure exited 0), so exit hard on failure.
        os._exit(rc)
    app.close()
    sys.exit(0)
