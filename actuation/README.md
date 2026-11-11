# actuation

Low-level actuator layer: **joint targets in, joint state out**, nothing smarter.

Goals, trajectories, IK, and perception belong in [`robot_software/`](../robot_software/).

Backends:
- [`sim/`](sim/): Isaac Sim
- [`feetech/`](feetech/): real STS3215 servos
