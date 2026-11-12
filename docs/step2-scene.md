# Step 2: Isaac Sim scene

**Status:** not started. Step 1 (robot USD) is done; see [`robot_description/`](../robot_description/).

**Goal:** a headless Isaac Sim scene with the arm mounted on a table and a set of blocks in
reach, that loads and settles stably. Later steps build on it: step 3 drives the arm through
`actuation/sim`, and step 4 picks and stacks blocks.

## Deliverables

| File | What |
|---|---|
| `configs/scene.yaml` | Table size, arm mount pose, block size/mass/colour/count, block start layout, physics dt |
| `simulation/scenes/build_scene.py` | Builds the scene from the config: ground, table, arm (referencing the step 1 USD), blocks, lights, physics scene. Saves `simulation/scenes/tower_scene.usda` |
| `simulation/scripts/check_scene.py` | Headless check (exits non-zero on failure), like `check_robot_usd.py` |
| `docs/brev-setup.md` | Updated with anything new the instance needed |

Run both with `docker/run.sh`, the same way as step 1.

## Acceptance checks (`check_scene.py`)

- Scene loads; the arm articulation and every block are found.
- After 5 s of simulation: blocks are still on the table (none fell or flew off), their
  velocities are near zero, and no block is penetrating the table.
- Arm base stays fixed on the table.
- Every block's start position is within the arm's reach. To start with, a distance check
  against a reach radius; real IK comes in step 4.
- Arm can move to a pose above each block without hitting the table. This uses joint targets
  only, no grasping yet.

## Decisions needed from you

1. **Blocks:** the real blocks you'll stack, so the sim matches the hardware:
   - size (cube edge in mm)
   - material and rough mass
   - how many
2. **Table:** surface size, and where the arm is mounted on it (edge or centre).
3. **Tower goal:** how tall, and where on the table it's built.
4. **Camera:** is the wrist camera enough, or do you also want a fixed overhead camera? This
   doesn't block step 2, but it decides what the scene includes.

## Inherited open issues

- **Vulkan fails in the container** (`ERROR_INCOMPATIBLE_DRIVER`). It does **not** block the
  physics-only scene and checks above. It **does** block:
  - the GUI or WebRTC visual check of the scene
  - camera sensors and rendering (perception)

  The first diagnostic to run is in [brev-setup.md](brev-setup.md#open-issues).
- **Arm base sits ~2.5 mm above the origin** in `check_robot_usd.py`. Find out why before
  placing the arm on the table: it could be a mount offset in the URDF, or the importer's
  root joint.

## Before starting, on a new Brev instance

The deployment was deleted on 2026-11-12, so the instance setup must be redone. Recommended:
first do the small automation PR that turns [brev-setup.md](brev-setup.md) into one script,
`scripts/brev-setup.sh`, and adds a single import+check command. Then step 2.
