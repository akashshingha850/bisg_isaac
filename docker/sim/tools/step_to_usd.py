"""
CAD (STEP) -> raw USD with the Isaac CAD Converter (HOOPS), plus a part listing. Step 1 of the raptor asset pipeline
(docker/sim/assets/README.md); step 2 turns the raw USD into the Pegasus-ready vehicle.

    docker run --rm --gpus all -e ACCEPT_EULA=Y -e PRIVACY_CONSENT=Y -v $PWD:/workspace -w /workspace --entrypoint /isaac-sim/python.sh \
        bisg/sim:6.0.0 docker/sim/tools/step_to_usd.py --step docker/sim/assets/vehicles/raptor/cad/raptor.step --out /workspace/docker/sim/cache/raptor_raw
Writes <out>/<name>.usd and <out>/<name>_parts.json (prim path, bbox min/max in metres, mesh count) for choosing which parts form `body`.
"""
import argparse
import json
import os

ap = argparse.ArgumentParser()
ap.add_argument("--step", required=True)
ap.add_argument("--out", required=True, help="output directory")
ap.add_argument("--tess-lod", type=int, default=3, help="tessellation level of detail (0 coarse .. 5 fine)")
args = ap.parse_args()

from isaacsim import SimulationApp  # noqa: E402

app = SimulationApp({"headless": True})

from isaacsim.core.utils.extensions import enable_extension  # noqa: E402,WPS433

enable_extension("omni.kit.converter.hoops_core")
app.update()

import omni.converter.hoops as hoops  # noqa: E402
from pxr import Usd, UsdGeom  # noqa: E402

os.makedirs(args.out, exist_ok=True)
name = os.path.splitext(os.path.basename(args.step))[0]
usd_path = os.path.join(args.out, f"{name}.usd")

p = hoops.Parameters()
p.tessLOD = args.tess_lod
p.upAxis = hoops.UpAxis.eZ if hasattr(hoops.UpAxis, "eZ") else p.upAxis
p.instancingStyle = hoops.InstancingStyle.eNone
p.compositionStyle = hoops.CompositionStyle.eNone
p.useMaterials = True
p.convertMetadata = True
rc, msg = hoops.Converter(p).convert(os.path.abspath(args.step), usd_path)
ok = os.path.exists(usd_path)  # the first tuple item is a status code (0 = success), not a bool
print(f"[step_to_usd] convert -> {usd_path}: rc={rc} {msg}")

if ok:
    stage = Usd.Stage.Open(usd_path)
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_], useExtentsHint=False)
    mpu = UsdGeom.GetStageMetersPerUnit(stage)
    parts = []
    for prim in stage.Traverse():
        meshes = [q for q in Usd.PrimRange(prim) if q.IsA(UsdGeom.Mesh)]
        if not meshes or prim.IsA(UsdGeom.Mesh):
            continue
        # only report prims that are the lowest ancestor containing all their meshes' parents' chain (assembly nodes)
        r = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if r.IsEmpty():
            continue
        lo, hi = r.GetMin(), r.GetMax()
        parts.append({"path": str(prim.GetPath()), "meshes": len(meshes),
                      "min_m": [round(lo[i] * mpu, 4) for i in range(3)], "max_m": [round(hi[i] * mpu, 4) for i in range(3)]})
    with open(os.path.join(args.out, f"{name}_parts.json"), "w") as f:
        json.dump({"meters_per_unit": mpu, "up_axis": str(UsdGeom.GetStageUpAxis(stage)), "parts": parts}, f, indent=1)
    print(f"[step_to_usd] metersPerUnit={mpu} upAxis={UsdGeom.GetStageUpAxis(stage)} nodes={len(parts)}")

app.close()
