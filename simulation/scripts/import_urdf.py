"""Convert the SO-ARM101 URDF to USD with the Isaac Sim URDF importer.

Run from the repo root with Isaac Sim's python, e.g.:
    ./python.sh simulation/scripts/import_urdf.py          # Isaac Sim install
    python simulation/scripts/import_urdf.py               # `pip install isaacsim` venv

Idempotent: re-running overwrites the output USD.
Targets Isaac Sim 5.x (`isaacsim.asset.importer.urdf`).
"""

import argparse
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--urdf", default=os.path.join(REPO, "robot_description/urdf/so101_new_calib_camera.urdf"))
parser.add_argument("--out", default=os.path.join(REPO, "robot_description/usd/so101.usd"))
# Placeholder drive gains, in USD angular-drive units (per degree). Tuned to the STS3215 later.
parser.add_argument("--stiffness", type=float, default=2.0, help="N*m/deg")
parser.add_argument("--damping", type=float, default=0.1, help="N*m*s/deg")
args = parser.parse_args()

# SimulationApp must start before any omni/pxr import.
from isaacsim import SimulationApp  # noqa: E402

app = SimulationApp({"headless": True})

import omni.kit.commands  # noqa: E402
from isaacsim.core.utils.extensions import enable_extension  # noqa: E402

enable_extension("isaacsim.asset.importer.urdf")
from isaacsim.asset.importer.urdf import _urdf  # noqa: E402
from pxr import Usd, UsdPhysics  # noqa: E402


def set_cfg(cfg, name, value):
    """Set an import-config field, warning (not failing) if this Isaac Sim version lacks it."""
    if hasattr(cfg, name):
        setattr(cfg, name, value)
    else:
        print(f"[import_urdf] warning: import config has no '{name}', skipped")


def main() -> int:
    urdf = os.path.abspath(args.urdf)
    out = os.path.abspath(args.out)
    if not os.path.isfile(urdf):
        print(f"[import_urdf] URDF not found: {urdf}")
        return 1
    os.makedirs(os.path.dirname(out), exist_ok=True)

    _, cfg = omni.kit.commands.execute("URDFCreateImportConfig")
    set_cfg(cfg, "fix_base", True)                # arm is bolted to the table
    set_cfg(cfg, "merge_fixed_joints", False)     # keep gripper_frame_link (TCP) and wrist_camera_link
    set_cfg(cfg, "import_inertia_tensor", True)
    set_cfg(cfg, "distance_scale", 1.0)           # URDF is in metres
    set_cfg(cfg, "density", 0.0)                  # use URDF masses
    set_cfg(cfg, "convex_decomp", True)
    set_cfg(cfg, "self_collision", False)
    set_cfg(cfg, "make_default_prim", True)
    set_cfg(cfg, "create_physics_scene", False)   # scenes own their physics scene
    set_cfg(cfg, "default_drive_type", _urdf.UrdfJointTargetType.JOINT_DRIVE_POSITION)

    ok, prim_path = omni.kit.commands.execute(
        "URDFParseAndImportFile",
        urdf_path=urdf,
        import_config=cfg,
        dest_path=out,
        get_articulation_root=True,
    )
    if not ok or not os.path.isfile(out):
        print(f"[import_urdf] import failed (ok={ok}, prim={prim_path})")
        return 1
    print(f"[import_urdf] imported {urdf} -> {out} (articulation root: {prim_path})")

    # Set drive gains directly on the joints: the importer's gain fields differ between versions.
    stage = Usd.Stage.Open(out)
    n = 0
    for prim in stage.Traverse():
        if prim.IsA(UsdPhysics.RevoluteJoint):
            drive = UsdPhysics.DriveAPI.Apply(prim, "angular")
            drive.CreateTypeAttr("force")
            drive.CreateStiffnessAttr().Set(args.stiffness)
            drive.CreateDampingAttr().Set(args.damping)
            n += 1
    stage.GetRootLayer().Save()
    print(f"[import_urdf] set drives on {n} revolute joints (stiffness={args.stiffness}, damping={args.damping})")
    if n != 6:
        print(f"[import_urdf] expected 6 revolute joints, found {n}")
        return 1
    return 0


if __name__ == "__main__":
    rc = main()
    app.close()
    sys.exit(rc)
