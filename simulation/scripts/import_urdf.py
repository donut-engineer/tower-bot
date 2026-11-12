"""Convert the SO-ARM101 URDF to USD with the Isaac Sim URDF importer.

Run from the repo root:
    docker/run.sh simulation/scripts/import_urdf.py

Writes into robot_description/usd/. The importer picks the file layout and the script prints
the final USD path. Idempotent: re-running overwrites the output.
Targets Isaac Sim 6.2.0 (docker/compose.yaml): `URDFImporterConfig` + `URDFImporter`.
"""

import argparse
import glob
import os
import re
import shutil
import sys
import traceback
import xml.etree.ElementTree as ET

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--urdf", default=os.path.join(REPO, "robot_description/urdf/so101_new_calib_camera.urdf"))
parser.add_argument("--out-dir", default=os.path.join(REPO, "robot_description/usd"))
# Placeholder drive gains (SI units). Tuned to the STS3215 later.
parser.add_argument("--stiffness", type=float, default=100.0, help="N*m/rad")
parser.add_argument("--damping", type=float, default=5.0, help="N*m*s/rad")
# The importer writes physics into a "Physics" variant set (none/physics/physx/mujoco) with no
# default selection, which leaves the robot without joints. Select one as the default.
parser.add_argument("--physics", default="physx", choices=["physx", "physics", "mujoco", "none"])
args = parser.parse_args()

# SimulationApp must start before any omni/pxr import.
from isaacsim import SimulationApp  # noqa: E402

app = SimulationApp({"headless": True})


def main() -> int:
    from isaacsim.asset.importer.urdf import URDFImporter, URDFImporterConfig
    from pxr import Usd, UsdPhysics

    urdf = os.path.abspath(args.urdf)
    out_dir = os.path.abspath(args.out_dir)
    if not os.path.isfile(urdf):
        print(f"[import_urdf] URDF not found: {urdf}")
        return 1
    os.makedirs(out_dir, exist_ok=True)

    # The importer writes <out_dir>/<robot name>/ and picks <name>_1, _2, ... if that exists.
    # Remove earlier output so re-runs replace it.
    name = ET.parse(urdf).getroot().get("name")
    for d in glob.glob(os.path.join(out_dir, name + "*")):
        if os.path.isdir(d) and re.fullmatch(re.escape(name) + r"(_\d+)?", os.path.basename(d)):
            print(f"[import_urdf] removing old output {d}")
            shutil.rmtree(d)

    cfg = URDFImporterConfig(
        urdf_path=urdf,
        usd_path=out_dir,                          # a directory; the importer names the file
        fix_base=True,                             # arm is bolted to the table
        merge_fixed_joints=False,                  # keep gripper_frame_link (TCP) and wrist_camera_link
        collision_type="Convex Decomposition",
        allow_self_collision=False,
        joint_drive_type="force",
        joint_target_type="position",
        override_joint_stiffness=args.stiffness,
        override_joint_damping=args.damping,
    )
    usd_path = URDFImporter(cfg).import_urdf()
    if not usd_path or not os.path.isfile(usd_path):
        print(f"[import_urdf] import failed (returned {usd_path!r})")
        return 1
    print(f"[import_urdf] imported {urdf} -> {usd_path}")

    stage = Usd.Stage.Open(usd_path)
    vset = stage.GetDefaultPrim().GetVariantSets().GetVariantSet("Physics")
    if args.physics not in vset.GetVariantNames():
        print(f"[import_urdf] no '{args.physics}' physics variant; found {vset.GetVariantNames()}")
        return 1
    vset.SetVariantSelection(args.physics)
    stage.GetRootLayer().Save()
    print(f"[import_urdf] default physics variant: {args.physics}")

    n = sum(1 for p in stage.Traverse() if p.IsA(UsdPhysics.RevoluteJoint))
    print(f"[import_urdf] revolute joints in output: {n}")
    if n != 6:
        print("[import_urdf] expected 6 revolute joints")
        return 1
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    except Exception:
        traceback.print_exc()
        rc = 1
    print(f"[import_urdf] exit {rc}", flush=True)
    sys.stderr.flush()
    if rc != 0:
        # Kit swallowed the exit code on the first run (failure exited 0), so exit hard on failure.
        os._exit(rc)
    app.close()
    sys.exit(0)
