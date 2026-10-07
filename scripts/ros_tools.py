#!/usr/bin/env python3
"""Read / toggle docker/ros/tools.yaml (the ROS 2 tools bisg-ros runs on the host display).

  ros_tools.py list              name, enabled, command
  ros_tools.py enabled           names with enabled: true, one per line
  ros_tools.py exists NAME       exit 0 if NAME is defined
  ros_tools.py cmd NAME [ARG..]  the shell command (ARGs replace the yaml args), quoted
  ros_tools.py exe NAME          the first word of exec (the process name to look for)
  ros_tools.py set NAME on|off   flip `enabled:` in place (comments are kept)
"""
import os
import re
import shlex
import sys

import yaml

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docker", "ros", "tools.yaml")


def load():
    with open(FILE) as f:
        return (yaml.safe_load(f) or {}).get("tools") or {}


def main(argv):
    if not argv:
        sys.exit(__doc__)
    cmd, tools = argv[0], load()
    name = argv[1] if len(argv) > 1 else None
    if cmd == "list":
        for n, t in tools.items():
            print(f"{n:12} {'on ' if t.get('enabled') else 'off'}  {' '.join([t['exec']] + [str(a) for a in t.get('args') or []])}")
    elif cmd == "enabled":
        print("\n".join(n for n, t in tools.items() if t.get("enabled")))
    elif cmd in ("exists", "cmd", "exe", "set"):
        if name not in tools:
            sys.exit(f"unknown tool '{name}' (have: {', '.join(tools)})")
        t = tools[name]
        if cmd == "cmd":
            args = argv[2:] if len(argv) > 2 else [str(a) for a in t.get("args") or []]
            print(t["exec"] + "".join(" " + shlex.quote(a) for a in args))
        elif cmd == "exe":
            print(shlex.split(t["exec"])[0])
        elif cmd == "set":
            val = {"on": "true", "off": "false"}.get(argv[2] if len(argv) > 2 else "")
            if val is None:
                sys.exit("set NAME on|off")
            text = open(FILE).read()
            new, n = re.subn(rf"(?ms)(^  {re.escape(name)}:\s*(?:#.*)?\n\s+enabled:\s*)(true|false)", rf"\g<1>{val}", text, count=1)
            if not n:
                sys.exit(f"could not find '{name}: enabled:' in {FILE}")
            open(FILE, "w").write(new)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
