#!/usr/bin/env python3
"""
Sync the raptor model from Onshape (docker/sim/assets/README.md): ./bisg raptor sync [--force] [--download-only]

  1. Onshape assembly (raptor.yaml `cad.onshape`) -> STEP -> cad/raptor.step      (REST API, stdlib only)
  2. parts HIDDEN in the Onshape assembly -> cad/onshape_hidden.json              (the STEP export includes hidden parts;
     build_raptor.py deactivates them in the visual, next to the hand-kept `cad.exclude` of raptor.yaml)
  3. step_to_usd.py -> raptor_visual.usd, build_raptor.py -> raptor.usd + raptor_summary.json   (bisg/sim image, ~6 min)

Skipped when nothing changed: cad/onshape_hidden.json keeps the document microversion of the last complete sync (it moves with
every edit in the Onshape document); the same microversion + built outputs = "up to date" in one API call. --force redoes it
(also needed after editing raptor.yaml / build_raptor.py, which the microversion does not see).

Onshape keys (Account > Developer > API keys, read permissions): ONSHAPE_ACCESS_KEY / ONSHAPE_SECRET_KEY in the environment,
else in docker/.env (git-ignored), else in ~/tools/onshape-mcp/.env. Never in a tracked file.
"""
import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

import yaml

ASSET = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ASSET, "../../../../.."))
CACHE = os.path.join(ROOT, "docker/sim/cache")
API = "https://cad.onshape.com/api/v11"


def keys():
    vals = {k: os.environ.get(k) for k in ("ONSHAPE_ACCESS_KEY", "ONSHAPE_SECRET_KEY")}
    for f in (os.path.join(ROOT, "docker/.env"), os.path.expanduser("~/tools/onshape-mcp/.env")):
        if all(vals.values()) or not os.path.exists(f):
            continue
        for line in open(f):
            k, sep, v = line.strip().partition("=")
            if sep and k in vals and not vals[k]:
                vals[k] = v.strip().strip("\"'")
    if not all(vals.values()):
        sys.exit("no Onshape keys: set ONSHAPE_ACCESS_KEY and ONSHAPE_SECRET_KEY in docker/.env (see the docstring)")
    return vals


def call(auth, method, url, body=None):
    req = urllib.request.Request(url, method=method, data=None if body is None else json.dumps(body).encode())
    req.add_header("Authorization", "Basic " + auth)
    req.add_header("Accept", "application/json;charset=UTF-8; qs=0.09")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        return urllib.request.urlopen(req, timeout=120).read()
    except urllib.error.HTTPError as e:
        sys.exit(f"Onshape {method} {url.split('onshape.com')[1]} -> {e.code} {e.read()[:300]!r}")


def token(name):
    """Prim-name token: the USD prim name keeps [A-Za-z0-9_] of the CAD name and drops ' <n>' (shortcut: a visible part
    whose name contains this token would also be dropped; build_raptor.py prints every dropped prim)."""
    return re.sub(r"[^A-Za-z0-9_]", "", re.sub(r"\s*<\d+>$", "", name))


def hidden_names(auth, ids):
    d = json.loads(call(auth, "GET", f"{API}/assemblies/d/{ids['document']}/w/{ids['workspace']}/e/{ids['element']}"
                        "?includeMateFeatures=false&includeNonSolids=false"))
    inst = {i["id"]: i["name"] for a in [d["rootAssembly"]] + d.get("subAssemblies", []) for i in a.get("instances", [])}
    names = {inst[o["path"][-1]] for o in d["rootAssembly"].get("occurrences", []) if o.get("hidden") and o["path"][-1] in inst}
    return sorted(names), d["rootAssembly"]["documentMicroversion"]


def export_step(auth, ids, out):
    base = f"{API}/assemblies/d/{ids['document']}/w/{ids['workspace']}/e/{ids['element']}"
    t = json.loads(call(auth, "POST", base + "/translations", {"formatName": "STEP", "storeInDocument": False}))
    for _ in range(120):
        t = json.loads(call(auth, "GET", f"{API}/translations/{t['id']}"))
        if t["requestState"] in ("DONE", "FAILED"):
            break
        time.sleep(5)
    if t["requestState"] != "DONE":
        sys.exit(f"STEP export {t['requestState']}: {t.get('failureReason')}")
    data = call(auth, "GET", f"{API}/documents/d/{ids['document']}/externaldata/{t['resultExternalDataIds'][0]}")
    with open(out + ".tmp", "wb") as f:
        f.write(data)
    os.replace(out + ".tmp", out)
    return len(data)


def docker(script, outdir, *extra):
    cmd = ["docker", "run", "--rm", "--gpus", "all", "-e", "ACCEPT_EULA=Y", "-e", "PRIVACY_CONSENT=Y", "-v", f"{ROOT}:/workspace",
           "-w", "/workspace", "--entrypoint", "/isaac-sim/python.sh", "bisg/sim:6.0.0", f"docker/sim/tools/{script}",
           *extra, "--out", "/workspace/" + os.path.relpath(outdir, ROOT)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=1500)
    print("\n".join(l for l in p.stdout.splitlines() if l.startswith(("[build]", "[step_to_usd]"))))
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--download-only", action="store_true", help="steps 1-2 only (no Isaac conversion)")
    ap.add_argument("--force", action="store_true", help="redo everything even if Onshape has not changed")
    args = ap.parse_args()

    ids = yaml.safe_load(open(f"{ASSET}/raptor.yaml"))["cad"]["onshape"]
    k = keys()
    auth = base64.b64encode(f"{k['ONSHAPE_ACCESS_KEY']}:{k['ONSHAPE_SECRET_KEY']}".encode()).decode()

    names, micro = hidden_names(auth, ids)
    state_file = f"{ASSET}/cad/onshape_hidden.json"
    state = json.load(open(state_file)) if os.path.exists(state_file) else {}
    outputs = [f"{ASSET}/{f}" for f in ("cad/raptor.step", "raptor_visual.usd", "raptor.usd", "raptor_summary.json")]
    if not args.force and state.get("built") and state.get("microversion") == micro and all(map(os.path.exists, outputs)):
        print(f"up to date: Onshape microversion {micro[:8]} is the one already built (--force to redo)")
        return
    tokens = sorted({token(n) for n in names})
    print(f"hidden in Onshape ({len(names)}): {', '.join(names) or '-'}  -> prim tokens {tokens}")
    size = export_step(auth, ids, f"{ASSET}/cad/raptor.step")
    print(f"cad/raptor.step written ({size / 1e6:.1f} MB)")
    def save(built):  # "exclude" is what build_raptor.py reads
        json.dump({"source": "Onshape assembly hidden instances (sync_onshape.py)", "microversion": micro, "built": built,
                   "names": names, "exclude": tokens}, open(state_file, "w"), indent=1)

    save(False)  # the STEP is new, the USDs are not yet
    if args.download_only:
        return

    os.makedirs(CACHE, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="raptor_sync_", dir=CACHE)
    os.chmod(tmp, 0o777)  # the container user (uid 1234) writes here
    try:
        raw, built = os.path.join(tmp, "raw"), os.path.join(tmp, "build")
        for d in (raw, built):
            os.mkdir(d)
            os.chmod(d, 0o777)
        # step_to_usd's last step (parts listing) may fail on file permissions; the USD is what counts
        docker("step_to_usd.py", raw, "--step", "/workspace/docker/sim/assets/vehicles/raptor/cad/raptor.step")
        if not os.path.exists(f"{raw}/raptor.usd"):
            sys.exit("step_to_usd produced no raptor.usd (run it by hand for the log)")
        shutil.copy(f"{raw}/raptor.usd", f"{ASSET}/raptor_visual.usd")
        p = docker("build_raptor.py", built)
        if p.returncode or not os.path.exists(f"{built}/raptor.usd"):
            sys.exit("build_raptor failed:\n" + p.stdout[-1500:])
        dropped = re.search(r"dropped (\[.*\])", p.stdout)
        dropped = dropped.group(1) if dropped else ""
        for t in tokens:
            if t not in dropped:
                print(f"note: hidden part '{t}' is not in the dropped list (inside an already-excluded parent, or renamed: check the list above)")
        old = json.load(open(f"{ASSET}/raptor_summary.json"))
        new = json.load(open(f"{built}/raptor_summary.json"))
        for f in ("raptor.usd", "raptor_summary.json"):
            shutil.copy(f"{built}/{f}", f"{ASSET}/{f}")
        diff = {key: (old.get(key), new[key]) for key in new if old.get(key) != new[key]}
        print("summary changes (old, new):", json.dumps(diff) if diff else "none (mass/CoM/mounts come from raptor.yaml, not the CAD)")
        save(True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
