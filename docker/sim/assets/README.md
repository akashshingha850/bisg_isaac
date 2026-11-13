# docker/sim/assets

`vehicles/raptor/` (Phase 4): the real quad (Raptor 5" cinewhoop: frame, Jetson Orin NX, ZED Mini, LW20) as a Pegasus vehicle.
It runs through the locator `docker/sim/sim.yaml` (the default `SIM_SCENARIO`): `scenario: configs/raptor_scenario.yaml` (common
settings), `vehicle: vehicles/raptor/raptor.yaml` (the vehicle entry: ZED/ToF mounts; also the build inputs below), `model:` the USD,
plus world, spawn pose and `px4_params: [raptor]`.

**Update from Onshape: `./bisg raptor sync`** (`vehicles/raptor/sync_onshape.py`) does all three steps below: it exports the assembly named in
`raptor.yaml` `cad.onshape` as STEP, skips the parts that are *hidden* in that assembly (the STEP export includes them; their names go to
`cad/onshape_hidden.json`, which `build_raptor.py` adds to `cad.exclude`), converts, builds and installs the USDs (~6 min, needs the sim
image and a free GPU). Keys: `ONSHAPE_ACCESS_KEY` / `ONSHAPE_SECRET_KEY` in `docker/.env` (read-only API key, My account > Developer).
It does nothing when the Onshape document has not changed since the last sync (`--force` redoes it, e.g. after editing `raptor.yaml`); `--download-only` stops after the STEP. Mass, CoM and mounts do not follow the CAD: they come from `raptor.yaml` (below).

Pipeline (each step runs in the `bisg/sim:6.0.0` image, command in the script's docstring; the container user cannot write
`docker/sim/assets`, so output goes to `docker/sim/cache/...` and is copied):
1. `cad/raptor.step` (Onshape export, metres) → `docker/sim/tools/step_to_usd.py` (Isaac CAD Converter) → `raptor_visual.usd` (raw CAD, Z up).
2. `raptor.yaml` (motors fitted to the 4 duct holes, mass groups, sensor mounts) → `docker/sim/tools/build_raptor.py` →
   `raptor.usd` (`/vehicle/body` + `rotor0..3` + `joint0..3`, CoM at the body origin, duct collision cylinders) and
   `raptor_summary.json` (numbers for the scenario: CoM, inertia, ZED/ToF mounts, rest height).
3. Frame convention: Onshape forward = −y, left = +x, up = +z; the build rotates it to FLU.
Masses, the thrust-plane height and the battery position in `raptor.yaml` are placeholders until the real drone is weighed.
