---
name: sim-launch
description: Start, stop, restart and diagnose the Isaac Sim + Pegasus + PX4 SITL stack (compose profiles sim / sim-headless), tail its logs, reset caches. Use when the user says start/stop/restart the sim, sim won't boot, black window, or headless run.
---

# sim-launch

Real commands live in `docs/runbook-sim.md`; this is the checklist Claude follows.

## Procedure (prefer the CLI: `./bisg up|wait|status|logs|smoke|down`, `./bisg debug ...`)
1. Preflight: `./bisg check` (driver ≥ 570, `nvidia` runtime in `docker info`, `xhost +local:` for GUI, ≥ 6 GB free VRAM, ≥ 50 GB disk).
2. Start:
   - GUI: `./bisg up gui`   headless: `./bisg up headless`   (both wait for PX4 ready; `--no-wait` to skip)
   - no argument: view and scenario come from `config/bisg.conf` (`SIM_VIEW`, `SIM_SCENARIO`); `./bisg config` shows the resolved values (docs/configuration.md)
   - scenario override: `./bisg up headless -c headless_fast` (name in `sim/configs/` or a path)
   - watch a headless run: `./bisg up web` (browser view on TCP `SIM_WEB_PORT`, survives a VS Code/SSH tunnel) or `./bisg up webrtc` (interactive WebRTC, needs UDP 47998 → LAN/VPN only); `gui+webrtc` gives you both halves, `./bisg view` prints the URLs. Never use a stream for a timing/regression run — both force rendering on. docs/remote-access.md.
   - shell: `./bisg shell` (running sim) / `./bisg shell ros`
3. Wait: cold boot 2–5 min (shader cache). "Ready" = launcher prints `[launch] sim ready` and PX4 prints `INFO  [commander] Ready for takeoff!`. Use `timeout 600` when scripting.
4. Stop: `docker compose ... down`. Confirm no stray `px4` process: `pgrep -a px4`.
5. Logs: `./bisg logs -f`; Isaac kit log: `./bisg debug kitlog`; evidence bundle: `./bisg debug report`.

## Diagnosis checklist
- Window never appears → X11: `echo $DISPLAY`, `xhost`, `/tmp/.X11-unix` mounted.
- Boots then exits → kit log for `Failed to create any GPU devices` (driver/runtime) or EULA env vars missing.
- Very slow → shader cache volume missing (re-compiles every start); check named volumes exist. For real tuning use `./bisg debug perf` and `docs/performance.md` (NVIDIA Sim Performance Optimization Handbook; `perf:` knobs in the scenario YAML, and the `headless_fast` profile for tests).
- GPU container will not start at all with an NVML "Driver/library version mismatch" → the host driver was upgraded without a reboot; `./bisg check` reports it.
- PX4 not connecting → hand over to `px4-sitl` skill (port 4560+i, TCP connect order).
- Cache reset (last resort): remove the `kit`/`glcache`/`computecache` volumes, not `ov`/`pip`.

## Never
- Do not run Isaac Sim natively on the host as part of a workflow (ADR-002).
- Do not leave a GUI sim running while starting headless tests (VRAM).
