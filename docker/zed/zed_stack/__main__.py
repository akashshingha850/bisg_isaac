"""python3 -m zed_stack <command> — inspect, validate and apply docker/zed/zed.yaml (no ROS, no containers needed).

  plan [--sim] [--config F]       modules on/off, topics each one publishes, services that start
  compile [--sim] -o FILE         write the zed_wrapper parameter override file
  services [--sim]                names of the compose services to start next to the wrapper (one per line)
  set KEY=VALUE [...]             edit docker/zed/zed.yaml in place, comments kept:  set object_detection.enabled=true
  derive -o FILE KEY=VALUE [...]  write a validated COPY of the config with overrides (the original is untouched); used by `./bisg zed bench`
"""
import argparse
import os
import re
import sys

import yaml

from . import config, topics


def cmd_plan(args):
    cfg = config.load(args.config, sim=args.sim)
    print(f"config: {cfg.path}{'  (sim deltas applied)' if cfg.sim else ''}")
    print(f"\nZED SDK modules (zed_wrapper, camera {config.CAMERA_MODEL})")
    for name, (section, _, sdk) in config.MODULES.items():
        on = cfg.enabled(name)
        print(f"  {'ON ' if on else 'off'}  {name:<20} {sdk}")
        if on:
            for t in topics.module_topics(cfg, name):
                print(f"         /drone_<n>/zed/zed_node/{t}")
    print("\nservices")
    svc = cfg.services()
    bridge = cfg.bridge_modules()
    print(f"  {'ON ' if bridge else 'off'}  px4_bridge  (compose: zed-bridge)")
    for m in config.SERVICES["px4_bridge"][1]:
        state = "ON " if m in bridge else "off"
        print(f"         {state} {m:<18} {topics.BRIDGE[m][0]}  ->  {topics.BRIDGE[m][1]}")
    v = svc["qgc_video"]
    shape = f"2x2 {v['width']}px: left|chase / depth|flow" if v["layout"] == "grid" else f"single topic ({v['topic'] or 'left image'})"
    print(f"  {'ON ' if v['enabled'] else 'off'}  qgc_video   (compose: zed-video)  {shape}  -> udp://{v['host']}:{v['port']}")
    print(f"\nstart: wrapper{''.join(', ' + s for s in cfg.plan_services())}")


def cmd_compile(args):
    cfg = config.load(args.config, sim=args.sim)
    text = "# generated from docker/zed/zed.yaml by `python3 -m zed_stack compile` — do not edit\n" + cfg.wrapper_yaml()
    if args.output in (None, "-"):
        sys.stdout.write(text)
    else:
        with open(args.output, "w") as f:
            f.write(text)


def cmd_services(args):
    for s in config.load(args.config, sim=args.sim).plan_services():
        print(s)


def set_value(text, dotted, raw):
    """Replace the value of a.b.c in YAML text without touching comments or layout (block style only)."""
    path = dotted.split(".")
    lines = text.split("\n")
    indent_stack = []          # (indent, key)
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)([A-Za-z0-9_\-]+):(\s*)(.*)$", line)
        if not m or line.lstrip().startswith("#"):
            continue
        ind = len(m.group(1))
        while indent_stack and indent_stack[-1][0] >= ind:
            indent_stack.pop()
        indent_stack.append((ind, m.group(2)))
        if [k for _, k in indent_stack] == path:
            rest = m.group(4)
            if not rest or rest.startswith("#") or rest.startswith("{"):
                raise config.ConfigError(f"{dotted} is a block, not a single value")
            comment = re.search(r"\s+#.*$", rest)
            tail = comment.group(0) if comment else ""
            pad = (m.group(3) or " ")
            lines[i] = f"{m.group(1)}{m.group(2)}:{pad}{raw}{tail}"
            return "\n".join(lines)
    raise config.ConfigError(f"{dotted}: no such key in the file")


def cmd_set(args):
    path = args.config or config.DEFAULT_CONFIG
    with open(path) as f:
        text = f.read()
    for item in args.assignments:
        if "=" not in item:
            raise config.ConfigError(f"'{item}': expected KEY=VALUE")
        key, raw = item.split("=", 1)
        yaml.safe_load(raw)            # must parse as a YAML scalar
        text = set_value(text, key, raw)
    # validate before writing
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(text)
    try:
        config.load(tmp)
    except config.ConfigError as e:
        os.unlink(tmp)
        raise config.ConfigError(str(e).replace(tmp, path) + " — file not changed")
    os.replace(tmp, path)
    for item in args.assignments:
        print(f"set {item}")


def cmd_derive(args):
    import copy
    cfg = config.load(args.config, sim=False)
    data = copy.deepcopy(cfg.data)
    raw = yaml.safe_load(open(args.config or config.DEFAULT_CONFIG))     # keep the sim: block of the source file
    data["sim"] = raw.get("sim", {})
    for item in args.assignments:
        key, _, val = item.partition("=")
        node = data
        parts = key.split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = yaml.safe_load(val)
    config.StackConfig(data, args.output, sim=True).wrapper_params()      # validate (sim and plain)
    config.StackConfig(data, args.output, sim=False).wrapper_params()
    config.StackConfig(data, args.output, sim=True).services()
    with open(args.output, "w") as f:
        f.write("# derived by `python3 -m zed_stack derive` - do not edit\n")
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)
    print(f"wrote {args.output}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="zed_stack", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("plan", cmd_plan), ("compile", cmd_compile), ("services", cmd_services)):
        p = sub.add_parser(name)
        p.add_argument("--sim", action="store_const", const=True, default=None, help="apply the sim: deltas (default: $ZED_STACK_SIM=1)")
        p.add_argument("--config", help="default docker/zed/zed.yaml or $ZED_STACK_CONFIG")
        if name == "compile":
            p.add_argument("-o", "--output")
        p.set_defaults(fn=fn)
    p = sub.add_parser("derive")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--config")
    p.add_argument("assignments", nargs="*", metavar="KEY=VALUE")
    p.set_defaults(fn=cmd_derive)
    p = sub.add_parser("set")
    p.add_argument("assignments", nargs="+", metavar="KEY=VALUE")
    p.add_argument("--config")
    p.set_defaults(fn=cmd_set)
    args = ap.parse_args(argv)
    try:
        args.fn(args)
    except config.ConfigError as e:
        print(f"zed_stack: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
