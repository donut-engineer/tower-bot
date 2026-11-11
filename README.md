# tower-bot

An SO-ARM101 robot arm that builds towers out of blocks. Developed in simulation first
(NVIDIA Isaac Sim, run standalone), then deployed to the real arm. Robot code is C++.

## Layout

```
tower-bot/
├── robot_description/   # SO-ARM101 model: URDF, meshes, USD
├── simulation/          # Isaac Sim scenes and launch scripts
├── robot_software/      # high-level: tower logic, planning, perception
├── actuation/           # low-level: joint targets in, joint state out
│   ├── sim/             #   backend → Isaac Sim
│   └── feetech/         #   backend → real STS3215 servos
├── configs/             # shared configuration
└── docs/                # design notes and documentation
```

## Layer rule

`robot_software` → `actuation` → (`sim` | `feetech`)

`robot_software` never knows which actuation backend is active.
