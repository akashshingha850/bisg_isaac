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
   - scenario override: `./bisg up headless -c headless_fast` (name in `docker/sim/configs/` or a path)
   - watch a headless run: `./bisg up web` (browser view on TCP `SIM_WEB_PORT`, survives a VS Code/SSH tunnel) or `./bisg up webrtc` (interactive WebRTC, needs UDP 47998 → LAN/Tailscale only); `gui+webrtc` gives you both halves, `./bisg view` prints the URLs. Never use a stream for a timing/regression run — both force rendering on. docs/remote-access.md.
   - shell: `./bisg shell` (running sim) / `./bisg shell ros`
   - real ZED SDK in the sim: `./bisg up headless`, then `./bisg zed up` / `./bisg zed check` (skill `zed-sdk`; needs `./bisg zed build` once). Restart the sim whenever the wrapper restarts.
3. Wait: Isaac Sim 6.0 boots in ~30 s warm and ~190 s when the shader cache is empty (first boot, or after `./bisg debug clean-cache`); the launcher prints `[launch] INFO boot +Ns: <phase>` lines so you can see where the time goes. "Ready" = launcher prints `[launch] sim ready` and PX4 prints `INFO  [commander] Ready for takeoff!`. Use `timeout 600` when scripting.
4. Stop: `docker compose ... down`. Confirm no stray `px4` process: `pgrep -a px4`.
5. Logs: `./bisg logs -f`; Isaac kit log: `./bisg debug kitlog`; evidence bundle: `./bisg debug report`.

## Diagnosis checklist
- Window never appears → X11: `echo $DISPLAY`, `xhost`, `/tmp/.X11-unix` mounted.
- Boots then exits → kit log for `Failed to create any GPU devices` (driver/runtime) or EULA env vars missing.
- Boot always ~190 s → the 6.0 RTX shader cache is not persisted: `/isaac-sim/kit/cache` must be the named volume `isaac-cache-kit` (compose), otherwise every new container recompiles ~140 s of shaders (Kit log: `Waiting for compilation of ray tracing shaders`).
- Very slow steady state (rtf 0.3-0.5) → expected on 6.0: Pegasus's per-step Python (`docs/migration-errors.md` M8). `app.profile_s: 45` in a scenario prints a cProfile of the loop.
- `omni.services.livestream.nvcf` not found → that is the 5.1 WebRTC extension; 6.0 uses `omni.kit.livestream.app` (already in the launcher). The 6.0 base image's HEALTHCHECK is disabled in compose (it greps a Kit log path our launcher never writes).
- Container is up but `[launch] sim ready` never comes → read `./bisg logs` for the first Python traceback; `OmniHub ... Hub failed to launch` warnings are noise. For real tuning use `./bisg debug perf` and `docs/performance.md` (NVIDIA Sim Performance Optimization Handbook; `perf:` knobs in the scenario YAML, and the `headless_fast` profile for tests).
- GPU container will not start at all with an NVML "Driver/library version mismatch" → the host driver was upgraded without a reboot; `./bisg check` reports it.
- PX4 not connecting → hand over to `px4-sitl` skill (port 4560+i, TCP connect order).
- Cache reset (last resort): `./bisg debug clean-cache` (removes `isaac-cache-main`, `-compute`, `-kit`); not the `data`/`pkg` volumes.

## Never
- Do not run Isaac Sim natively on the host as part of a workflow (ADR-002).
- Do not leave a GUI sim running while starting headless tests (VRAM).
