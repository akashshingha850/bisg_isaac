#!/usr/bin/env python3
"""
ZED VIO calibration + benchmark + ablation campaign on THIS machine (docs/vio.md). Usually `./bisg vio bench [...]`.

For every flight (configs x reps from tests/vio_bench.yaml, interleaved per repetition):
  1. fresh sim: `./bisg down`, `./bisg all <view>` (the ZED SDK connects once per sim run, B18; its errors persist in a run)
  2. wait until the zed-bridge reports `odometry ok`; a wrapper that dies (R9) or never connects is an infra failure: restart, retry
  3. set the config's PX4 params live and read them back; wait until EKF2 fuses the ZED (cs_ev_vel + cs_ev_yaw): never fly without VIO
  4. tests/vio_bench.py in bisg-ros (OFFBOARD profile: hover, altitude steps, legs, yaw steps, yawed legs, square, hover, land)
  5. copy the PX4 log, tests/vio_eval.py on it (vio_eval.json, series.csv, topics.npz; vio_eval.png if matplotlib works)
Then tests/vio_report.py -> summary.md / summary.json / summary.csv / figures/*.svg and the verdict (exit 0 = PASS).

Output: $ARCHIVE_DIR/vio_bench/<YYYYmmdd-HHMMSS>-<host>/ (runs/<config>-r<k>/, machine.json, campaign.yaml, campaign.log).
`--resume <dir>` continues a stopped campaign (finished flights are kept). `--archive` copies it, without the .ulg files, to
archive/vio-bench/<name>/ in the repo.
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BISG = os.path.join(ROOT, "bisg")
SIM, ROS, ZED, BRIDGE = "bisg-sim", "bisg-ros", "bisg-zed-1", "bisg-zed-bridge-1"


class Infra(Exception):
    """The stack, not the VIO, failed (sim boot, ZED wrapper crash / no connect, EV never fused): retry on a fresh sim."""


# ---- shell -----------------------------------------------------------------------------------------------------------
LOG = None


def log(msg):
    line = f"[{dt.datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    if LOG:
        LOG.write(line + "\n")
        LOG.flush()


def sh(cmd, timeout=120, env=None, check=False):
    """Run a shell command, return (rc, stdout+stderr). rc 124 = timeout."""
    try:
        p = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, **(env or {})})
        out = p.stdout + p.stderr
        rc = p.returncode
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        rc = 124
    if check and rc != 0:
        raise Infra(f"`{cmd}` -> rc {rc}: {out.strip()[-300:]}")
    return rc, out


def poll(fn, timeout, every=5.0):
    end = time.time() + timeout
    while time.time() < end:
        r = fn()
        if r:
            return r
        time.sleep(every)
    return None


def running(name):
    return sh(f"docker inspect -f '{{{{.State.Running}}}}' {name}", 10)[1].strip() == "true"


# ---- config ----------------------------------------------------------------------------------------------------------
def load_yaml(path):
    try:
        import yaml
        with open(path) as fh:
            return yaml.safe_load(fh)
    except ImportError:                                   # no PyYAML on the host: the ros image has it
        rc, out = sh(f"docker run --rm -v {ROOT}:/workspace:ro --entrypoint python3 bisg/ros:jazzy -c "
                     f"\"import yaml,json,sys; print(json.dumps(yaml.safe_load(open('/workspace/{os.path.relpath(path, ROOT)}'))))\"", 120)
        if rc:
            sys.exit(f"cannot read {path}: install python3-yaml or build bisg/ros:jazzy ({out[-200:]})")
        return json.loads(out.strip().splitlines()[-1])


# ---- machine + software record (the "experimental setup") ------------------------------------------------------------
def first(pattern, text, default=""):
    m = re.search(pattern, text, re.M)
    return m.group(1).strip() if m else default


def machine_info():
    info = {"host": socket.gethostname(), "date": dt.datetime.now().isoformat(timespec="seconds")}
    info["cpu"] = first(r"Model name:\s*(.+)", sh("lscpu", 10)[1])
    info["cpu_threads"] = os.cpu_count()
    info["ram_gb"] = round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2 ** 30)
    gpus = sh("nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader", 20)[1].strip().splitlines()
    info["gpus"] = [g.strip() for g in gpus if g.strip()]
    info["os"] = first(r'PRETTY_NAME="(.+)"', open("/etc/os-release").read())
    info["kernel"] = os.uname().release
    info["docker"] = sh("docker version --format '{{.Server.Version}}'", 20)[1].strip()
    info["git_commit"] = sh("git rev-parse --short HEAD", 10)[1].strip()
    info["git_branch"] = sh("git rev-parse --abbrev-ref HEAD", 10)[1].strip()
    info["git_dirty"] = bool(sh("git status --porcelain -- tests docker/sim docker/zed config", 10)[1].strip())
    info["pegasus_commit"] = sh("git -C docker/sim/PegasusSimulator rev-parse --short HEAD", 10)[1].strip()
    info["env"] = {k: os.environ.get(k, "") for k in ("SIM_GPU", "ZED_GPU", "ZED_RMW", "RMW_IMPLEMENTATION", "ARCHIVE_DIR")}
    return info


def stack_versions():
    """Read from the running containers (call after a boot)."""
    v = {}
    for name in (SIM, ZED, ROS):
        rc, out = sh(f"docker inspect -f '{{{{.Config.Image}}}} {{{{.Image}}}}' {name}", 10)
        if rc == 0:
            img, iid = out.split()
            v[name] = {"image": img, "id": iid.replace("sha256:", "")[:12]}
    v["px4"] = sh(f"docker exec {SIM} git -C /opt/PX4-Autopilot describe --tags 2>/dev/null", 20)[1].strip()
    v["isaac_sim"] = sh(f"docker exec {SIM} bash -c 'cat /isaac-sim/VERSION 2>/dev/null | head -1'", 20)[1].strip()
    v["zed_sdk"] = first(r"ZED SDK Version: (\S+)", sh(f"docker logs {ZED} 2>&1 | grep -m1 'ZED SDK Version'", 20)[1])
    v["px4_param_files"] = first(r"px4 params from (\[.*?\])", sh(f"docker logs {SIM} 2>&1 | grep 'px4 params from' | head -1", 20)[1])
    return v


# ---- one flight ------------------------------------------------------------------------------------------------------
def boot(cfg):
    log("  boot: ./bisg down; ./bisg all " + cfg["view"])
    sh(f"{BISG} down", 180)
    env = {} if cfg.get("scenario", "default") == "default" else {"SIM_SCENARIO": cfg["scenario"]}
    rc, out = sh(f"{BISG} all {cfg['view']}", cfg["timeouts_s"]["boot"] + 60, env=env)
    if rc != 0 or not running(SIM):
        raise Infra(f"boot failed (rc {rc}): {out.strip()[-300:]}")


def wait_zed(cfg):
    def ready():
        if not running(ZED) and sh(f"docker inspect {ZED}", 10)[0] == 0:
            return "dead"
        out = sh(f"{BISG} zed status", 60)[1]
        return "ok" if re.search(r"^\s*odometry\s+ok", out, re.M) else None
    r = poll(ready, cfg["timeouts_s"]["zed"], 10)
    if r == "ok":
        return
    zlog = sh(f"docker logs {ZED} 2>&1 | tail -400", 20)[1]
    if "can't compare times with different time sources" in zlog:
        raise Infra("zed wrapper crashed: can't compare times with different time sources (R9)")
    if r == "dead":
        raise Infra("zed wrapper exited: " + zlog.strip().splitlines()[-1][-200:] if zlog.strip() else "zed wrapper exited")
    if "CONNECTING TO THE SIMULATION SERVER" in zlog and "Starting Positional Tracking" not in zlog:
        raise Infra("zed wrapper never connected to the sim stream (B18 class)")
    raise Infra(f"zed odometry not ok after {cfg['timeouts_s']['zed']} s")


def px4(cmd, timeout=30):
    return sh(f"{BISG} debug px4 {cmd}", timeout)[1]


def set_params(params):
    applied = {}
    for k, v in params.items():
        px4(f"param set {k} {v}")
        shown = first(rf"{k}\s*\[[^\]]*\]\s*:\s*(\S+)", px4(f"param show {k}"))
        try:
            ok = abs(float(shown) - float(v)) < 1e-6
        except ValueError:
            ok = False
        if not ok:
            raise Infra(f"param {k}={v} not applied (PX4 shows {shown!r})")
        applied[k] = float(shown)
    return applied


def wait_ev(cfg):
    def fused():
        out = px4("listener estimator_status_flags -n 1")
        flags = dict(re.findall(r"(cs_ev_\w+):\s*(True|False)", out))
        return flags if flags.get("cs_ev_vel") == "True" and flags.get("cs_ev_yaw") == "True" else None
    flags = poll(fused, cfg["timeouts_s"]["ekf_ev"], 5)
    if not flags:
        raise Infra("EKF2 does not fuse the ZED (cs_ev_vel/cs_ev_yaw false): not flying without VIO")
    return {k: v == "True" for k, v in flags.items()}


def rtf_between(t0, t1):
    out = sh(f"docker logs -t --since {t0} --until {t1} {SIM} 2>&1 | grep -o 'rtf=[0-9.]*'", 30)[1]
    vals = sorted(float(x.split("=")[1]) for x in out.split())
    if not vals:
        return {}
    return {"median": vals[len(vals) // 2], "min": vals[0], "max": vals[-1], "n": len(vals)}


def have(mod):
    return sh(f"python3 -c 'import {mod}'", 30)[0] == 0


def evaluate(run_dir):
    ulg = os.path.join(run_dir, "flight.ulg")
    args = "--series --save-npz {d}/topics.npz --out {d}"
    if have("numpy"):
        plot = " --plot" if have("matplotlib.pyplot") else ""
        rc, out = sh(f"python3 tests/vio_eval.py --ulog {ulg} {args.format(d=run_dir)}{plot}", 300)
    else:                                                    # no numpy on the host: the ros image has it
        sh(f"docker exec {ROS} rm -rf /tmp/vio_eval_run && docker exec {ROS} mkdir -p /tmp/vio_eval_run", 30)
        sh(f"docker cp {ulg} {ROS}:/tmp/vio_eval_run/flight.ulg", 120, check=True)
        rc, out = sh(f"docker exec {ROS} bash -c 'cd /workspace && PYTHONDONTWRITEBYTECODE=1 python3 tests/vio_eval.py "
                     f"--ulog /tmp/vio_eval_run/flight.ulg {args.format(d='/tmp/vio_eval_run')}'", 300)
        for f in ("vio_eval.json", "series.csv", "topics.npz"):
            sh(f"docker cp {ROS}:/tmp/vio_eval_run/{f} {run_dir}/", 120)
    with open(os.path.join(run_dir, "vio_eval.out"), "w") as fh:
        fh.write(out)
    return rc


def fly_once(cfg, name, params, run_dir):
    rec = {"config": name, "params_set": params}
    boot(cfg)
    wait_zed(cfg)
    rec["params_applied"] = set_params(params)
    rec["ekf_ev_flags_preflight"] = wait_ev(cfg)
    rec["versions"] = stack_versions()
    t0 = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    w0 = time.time()
    log(f"  flight: tests/vio_bench.py {cfg.get('flight_args', '')}")
    rc, out = sh(f"docker exec -e PYTHONUNBUFFERED=1 {ROS} bash -lc 'source /opt/ros/jazzy/setup.bash; "
                 f"python3 /workspace/tests/vio_bench.py --out /tmp/vio_bench {cfg.get('flight_args', '')}'",
                 cfg["timeouts_s"]["flight"])
    t1 = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(os.path.join(run_dir, "bench.log"), "w") as fh:
        fh.write(out)
    rec.update(flight_rc=rc, flight_wall_s=round(time.time() - w0), rtf=rtf_between(t0, t1),
               flight_summary=first(r"(\[vio_bench\] landed.*)", out) or first(r"(ABORT.*)", out),
               zed_alive_after=running(ZED))
    ulg = sh(f"docker exec {SIM} bash -lc 'ls -t $(find /tmp -name \"*.ulg\") 2>/dev/null | head -1'", 30)[1].strip()
    if not ulg:
        raise Infra("no PX4 log after the flight")
    sh(f"docker cp {SIM}:{ulg} {run_dir}/flight.ulg", 300, check=True)
    rec["eval_rc"] = evaluate(run_dir)
    return rec


def run_flight(cfg, name, rep, camp_dir):
    run_dir = os.path.join(camp_dir, "runs", f"{name}-r{rep}")
    path = os.path.join(run_dir, "run.json")
    if os.path.exists(path) and json.load(open(path)).get("status") == "done":
        log(f"{name} r{rep}: done before, kept")
        return
    os.makedirs(run_dir, exist_ok=True)
    infra = []
    for attempt in range(1, cfg["max_attempts"] + 1):
        log(f"{name} r{rep} attempt {attempt}/{cfg['max_attempts']}: params {cfg['configs'][name]['params'] or '(none)'}")
        try:
            rec = fly_once(cfg, name, cfg["configs"][name]["params"] or {}, run_dir)
        except Infra as exc:
            log(f"  infra failure: {exc}")
            infra.append({"attempt": attempt, "time": dt.datetime.now().isoformat(timespec="seconds"), "what": str(exc)})
            continue
        rec.update(status="done", rep=rep, attempts=attempt, infra_failures=infra)
        json.dump(rec, open(path, "w"), indent=1)
        log(f"  flight rc {rec['flight_rc']}, eval rc {rec['eval_rc']}, rtf {rec['rtf'].get('median')}: {rec['flight_summary']}")
        return
    json.dump({"config": name, "rep": rep, "status": "infra_failed", "infra_failures": infra}, open(path, "w"), indent=1)
    log(f"{name} r{rep}: gave up after {cfg['max_attempts']} attempts")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=os.path.join(HERE, "vio_bench.yaml"))
    ap.add_argument("--configs", default="", help="comma list (default: default_configs of the yaml)")
    ap.add_argument("--reps", type=int, default=0, help="flights per config (default: reps of the yaml)")
    ap.add_argument("--view", default="", help="SIM_VIEW for the flights (default: view of the yaml)")
    ap.add_argument("--root", default=os.path.join(os.path.expanduser(os.environ.get("ARCHIVE_DIR", "~/bisg-archive")), "vio_bench"))
    ap.add_argument("--resume", default="", help="campaign dir to continue")
    ap.add_argument("--archive", action="store_true", help="copy the campaign (no .ulg) to archive/vio-bench/<name>/ in the repo")
    ap.add_argument("--leave-up", action="store_true", help="leave the last sim running (default: ./bisg down at the end)")
    a = ap.parse_args()

    cfg = load_yaml(a.config)
    names = [c for c in (a.configs.split(",") if a.configs else cfg["default_configs"]) if c]
    for n in names:
        if n not in cfg["configs"]:
            sys.exit(f"unknown config {n!r}; known: {', '.join(cfg['configs'])}")
    cfg["reps"] = a.reps or cfg["reps"]
    cfg["view"] = a.view or cfg["view"]
    camp = a.resume or os.path.join(a.root, f"{dt.datetime.now():%Y%m%d-%H%M%S}-{socket.gethostname()}")
    os.makedirs(os.path.join(camp, "runs"), exist_ok=True)
    global LOG
    LOG = open(os.path.join(camp, "campaign.log"), "a")
    plan = {**cfg, "selected_configs": names,
            # the sim calibration under test, read now (the files may change later; the report must compare to what was flown)
            "restamp_latency_ms": float(first(r"^\s*restamp_latency_ms:\s*([0-9.]+)\s*#\s*measured",
                                              open(os.path.join(ROOT, "docker", "zed", "zed.yaml")).read(), "nan"))}
    if not os.path.exists(os.path.join(camp, "campaign.json")):
        json.dump(plan, open(os.path.join(camp, "campaign.json"), "w"), indent=1)
        shutil.copy(a.config, os.path.join(camp, "campaign.yaml"))
        json.dump(machine_info(), open(os.path.join(camp, "machine.json"), "w"), indent=1)
    log(f"campaign {camp}: configs {names} x {cfg['reps']} reps, view {cfg['view']} (~{6.5 * len(names) * cfg['reps']:.0f} min)")
    t_start = time.time()
    try:
        for rep in range(1, cfg["reps"] + 1):
            for name in names:
                run_flight(cfg, name, rep, camp)
    finally:
        if not a.leave_up:
            sh(f"{BISG} down", 180)
        log(f"campaign wall time {(time.time() - t_start) / 60:.0f} min")
    sys.path.insert(0, HERE)
    import vio_report
    verdict = vio_report.build(camp)
    if a.archive:
        dst = os.path.join(ROOT, "archive", "vio-bench", os.path.basename(camp.rstrip("/")))
        shutil.copytree(camp, dst, ignore=shutil.ignore_patterns("*.ulg"), dirs_exist_ok=True)
        log(f"archived (without .ulg) to {os.path.relpath(dst, ROOT)}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
