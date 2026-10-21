#!/usr/bin/env python3
"""Read / toggle docker/ros/bag.yaml (rosbag2 recording, ./bisg bag).

  ros_bag.py enabled              exit 0 if `enabled: true`
  ros_bag.py profiles             name and what it records, one per line
  ros_bag.py profile              the default profile name
  ros_bag.py cmd [PROFILE] OUT    the `ros2 bag record ...` command line for PROFILE (default: `profile:`), output dir OUT
  ros_bag.py set on|off           flip `enabled:` in place (comments are kept)
"""
import os
import re
import shlex
import sys

import yaml

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docker", "ros", "bag.yaml")


def load():
    with open(FILE) as f:
        return yaml.safe_load(f) or {}


def squash(rx):
    """The YAML folds the long patterns over several lines: drop the whitespace."""
    return re.sub(r"\s+", "", rx or "")


def regex_of(profiles, name, seen=()):
    if name in seen:
        sys.exit(f"bag.yaml: include loop at '{name}'")
    if name not in profiles:
        sys.exit(f"unknown bag profile '{name}' (have: {', '.join(profiles)})")
    p = profiles[name]
    parts = [regex_of(profiles, i, seen + (name,)) for i in p.get("include") or []]
    if p.get("regex"):
        parts.append(squash(p["regex"]))
    return "|".join(x for x in parts if x)


def command(cfg, name, out):
    profiles = cfg.get("profiles") or {}
    if name not in profiles:
        sys.exit(f"unknown bag profile '{name}' (have: {', '.join(profiles)})")
    p = profiles[name]
    argv = ["ros2", "bag", "record", "-o", out, "-s", str(cfg.get("storage", "mcap"))]
    if cfg.get("storage", "mcap") == "mcap" and cfg.get("preset", "none") != "none":
        argv += ["--storage-preset-profile", str(cfg["preset"])]
    if cfg.get("use_sim_time", False):
        argv.append("--use-sim-time")
    if int(cfg.get("max_bag_size_mb") or 0) > 0:
        argv += ["-b", str(int(cfg["max_bag_size_mb"]) * 1024 * 1024)]
    if p.get("all"):
        argv.append("-a")
    else:
        rx = regex_of(profiles, name)
        if not rx:
            sys.exit(f"bag profile '{name}' records nothing (no regex, no all: true)")
        argv += ["-e", f"^({rx})$"]
    if p.get("exclude_regex"):
        argv += ["--exclude-regex", f"^({squash(p['exclude_regex'])})$"]
    return " ".join(shlex.quote(a) for a in argv)


def main(argv):
    if not argv:
        sys.exit(__doc__)
    cfg, cmd = load(), argv[0]
    if cmd == "enabled":
        sys.exit(0 if cfg.get("enabled") else 1)
    elif cmd == "profile":
        print(cfg.get("profile", "flight"))
    elif cmd == "profiles":
        for n, p in (cfg.get("profiles") or {}).items():
            what = "all topics" if p.get("all") else f"regex{' + ' + ', '.join(p['include']) if p.get('include') else ''}"
            mark = "*" if n == cfg.get("profile") else " "
            print(f"{mark} {n:8} {what}{' minus exclude_regex' if p.get('exclude_regex') else ''}")
    elif cmd == "cmd":
        if len(argv) == 2:
            name, out = cfg.get("profile", "flight"), argv[1]
        elif len(argv) == 3:
            name, out = argv[1], argv[2]
        else:
            sys.exit("cmd [PROFILE] OUT")
        print(command(cfg, name, out))
    elif cmd == "set":
        val = {"on": "true", "off": "false"}.get(argv[1] if len(argv) > 1 else "")
        if val is None:
            sys.exit("set on|off")
        text = open(FILE).read()
        new, n = re.subn(r"(?m)^(enabled:[ \t]*)(true|false)", rf"\g<1>{val}", text, count=1)
        if not n:
            sys.exit(f"could not find a top-level 'enabled:' in {FILE}")
        open(FILE, "w").write(new)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
