#!/usr/bin/env bash
# Host preflight for the sim profile. Exit 0 = ready. Run from anywhere.
set -u
ok=0; warn=0; fail=0
pass(){ echo "  [ok]   $*"; }
wrn(){ echo "  [warn] $*"; warn=$((warn+1)); }
die(){ echo "  [FAIL] $*"; fail=$((fail+1)); }

echo "== bisg_isaac host check =="
# NVIDIA driver
if command -v nvidia-smi >/dev/null; then
  # A driver upgrade while the old kernel module is loaded breaks every GPU container until reboot.
  if ! nvidia-smi -L >/dev/null 2>&1; then
    err=$(nvidia-smi 2>&1 | head -2 | tr '\n' ' ')
    die "nvidia-smi fails: ${err}"
    if [[ "$err" == *"version mismatch"* ]]; then
      echo "         loaded kernel module: $(awk '{print $8}' /proc/driver/nvidia/version 2>/dev/null)"
      echo "         installed userspace:  $(nvidia-smi 2>&1 | grep -o 'NVML library version: .*')"
      echo "         the driver was upgraded while the old module is still loaded — REBOOT (or reload nvidia modules)."
      [[ -f /var/run/reboot-required ]] && echo "         /var/run/reboot-required is present: $(tr '\n' ' ' < /var/run/reboot-required.pkgs 2>/dev/null)"
    fi
    echo "== result: GPU unusable — fix the above before starting the sim =="
    exit 1
  fi
  drv=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1)
  gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
  vram_free=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)
  vram_total=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
  pass "GPU: $gpu, driver $drv, VRAM free ${vram_free}/${vram_total} MiB"
  [[ ${drv%%.*} -ge 570 ]] || die "driver ${drv} < 570 (Isaac Sim 5.1 needs >= 570)"
  [[ -f /var/run/reboot-required ]] && wrn "host reboot pending ($(tr '\n' ' ' < /var/run/reboot-required.pkgs 2>/dev/null | cut -c1-60)) — a driver/kernel upgrade will break GPU containers until you reboot"
  [[ ${vram_free} -ge 6000 ]] || wrn "less than 6 GB VRAM free; close other GPU apps before starting the sim"
else
  die "nvidia-smi not found"
fi
# Docker + nvidia runtime + compose
if command -v docker >/dev/null; then
  pass "docker $(docker --version | awk '{print $3}' | tr -d ,)"
  docker info 2>/dev/null | grep -q "Runtimes:.*nvidia" && pass "nvidia container runtime present" || die "nvidia runtime missing (install nvidia-container-toolkit, run: sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker)"
  docker compose version >/dev/null 2>&1 && pass "docker compose $(docker compose version --short)" || die "docker compose v2 missing"
  docker run --rm --runtime=nvidia --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi -L >/dev/null 2>&1 && pass "GPU visible inside a container" || wrn "GPU test container failed (image not pulled or runtime broken)"
else
  die "docker not found"
fi
# Display (GUI profile only)
if [[ -n "${DISPLAY:-}" ]]; then
  pass "DISPLAY=$DISPLAY"
  if command -v xhost >/dev/null; then
    xhost 2>/dev/null | grep -q "LOCAL:" && pass "xhost allows local containers" || wrn "run: xhost +local:   (needed for the GUI profile; container runs as uid 1234 isaac-sim)"
  fi
  [[ "${XDG_SESSION_TYPE:-}" == "wayland" ]] && wrn "Wayland session: Isaac GUI needs XWayland; if the window never appears, log in with an X11 session (plan.md §12)"
else
  wrn "DISPLAY unset: only the sim-headless profile will work"
fi
# Disk
free_gb=$(df -BG --output=avail "$(cd "$(dirname "$0")/.." && pwd)" | tail -1 | tr -dc '0-9')
[[ ${free_gb} -ge 60 ]] && pass "disk free ${free_gb} GB" || die "need >= 60 GB free for the Isaac image + caches (have ${free_gb} GB)"
docker_root=$(docker info 2>/dev/null | awk -F': ' '/Docker Root Dir/{print $2}')
[[ -n "$docker_root" ]] && echo "  [info] docker root: $docker_root ($(df -h "$docker_root" 2>/dev/null | tail -1 | awk '{print $4}') free)"
# Ports
for p in 4560 14540 14550 14580; do
  ss -lun 2>/dev/null | grep -q ":$p " && wrn "UDP port $p already in use (old PX4/QGC?)"; done
ss -ltn 2>/dev/null | grep -q ":4560 " && wrn "TCP 4560 in use (a PX4 SITL is still running?)"
echo "== result: $fail failed, $warn warnings =="
exit $(( fail > 0 ))
