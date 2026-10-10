"""
Probe: can the real ZED SDK give depth for TELEPORTED views (Kinetix view pools, docs/zed-sdk-sim.md "Pool depth probe")?

A standalone Isaac app (no drone, no PX4): world + a kinematic ZED_M twin streamed to the unmodified zed_wrapper exactly
like the launcher's rig (OnPlaybackTick -> sl.sensor.camera.ZED_Camera, same port). It waits for `<out>/go`, then
teleports the camera through a list of views, holding each for --dwell rendered frames, and saves for every view the
ground-truth depth (Isaac `distance_to_image_plane` on the asset's own left camera) and the wall-clock teleport time.
tests/zed_pool_probe_collect.py records the wrapper's depth meanwhile; tests/zed_pool_probe_eval.py compares them.

    docker compose -f docker/compose.yaml --profile sim-headless run -d --rm --name bisg-sim sim-headless \
        python /workspace/sim/tools/zed_pool_probe.py --out /tmp/zprobe
(full sequence: docs/zed-sdk-sim.md)
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, "/workspace/sim/launcher")
from zed_sdk_cfg import EXT_ID, ext_folder, stream_port  # noqa: E402  (stdlib only, safe before Kit)

ap = argparse.ArgumentParser()
ap.add_argument("--out", default="/tmp/zprobe")
ap.add_argument("--world", default="Full Warehouse", help="Pegasus SIMULATION_ENVIRONMENTS key")
ap.add_argument("--center", default="0,0", help="ring centre x,y (world, m)")
ap.add_argument("--radius", type=float, default=3.0)
ap.add_argument("--yaws", type=int, default=12, help="views per ring")
ap.add_argument("--heights", default="1.0,2.0")
ap.add_argument("--dwell", type=int, default=40, help="rendered frames per view")
ap.add_argument("--revisit", type=int, default=4, help="repeat the first N views at the end")
ap.add_argument("--go-timeout", type=float, default=900.0, help="s to wait for <out>/go (wrapper connected)")
a = ap.parse_args()

from isaacsim import SimulationApp  # noqa: E402

app = SimulationApp({"headless": True, "renderer": "RaytracedLighting", "width": 1280, "height": 720,
                     "extra_args": ["--ext-folder", ext_folder(), "--enable", EXT_ID]})

import numpy as np  # noqa: E402
import omni.graph.core as og  # noqa: E402
import omni.replicator.core as rep  # noqa: E402
import omni.timeline  # noqa: E402
import omni.usd  # noqa: E402
from isaacsim.core.utils.prims import set_targets  # noqa: E402
from pxr import Gf, UsdGeom, UsdPhysics  # noqa: E402
from scipy.spatial.transform import Rotation  # noqa: E402

from pegasus.simulator.params import SIMULATION_ENVIRONMENTS  # noqa: E402
from sl.sensor.camera.utils import get_camera_usd_path  # noqa: E402


def log(msg):
    print(f"[zprobe] {msg}", flush=True)


os.makedirs(a.out, exist_ok=True)
stage = omni.usd.get_context().get_stage()
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
stage.DefinePrim("/World/layout", "Xform").GetReferences().AddReference(SIMULATION_ENVIRONMENTS[a.world])

zed_path = "/World/zed_probe"
zed = stage.DefinePrim(zed_path, "Xform")
zed.GetReferences().AddReference(get_camera_usd_path("ZED_M"))
for _ in range(5):
    app.update()                                       # let the references compose
for p in [zed, *[q for q in stage.Traverse() if str(q.GetPath()).startswith(zed_path + "/")]]:
    if p.HasAPI(UsdPhysics.RigidBodyAPI):              # a teleported sensor: kinematic, never simulated
        UsdPhysics.RigidBodyAPI(p).CreateKinematicEnabledAttr(True)
cams = [str(q.GetPath()) for q in stage.Traverse()
        if str(q.GetPath()).startswith(zed_path) and q.IsA(UsdGeom.Camera)]
left = next((c for c in cams if "left" in c.lower()), cams[0] if cams else None)
log(f"camera prims {cams}; ground truth from {left}")
if left is None:
    raise SystemExit("[zprobe] no camera prim in the ZED_M asset")


def set_pose(pos, yaw_deg, pitch_down_deg):
    rot = Rotation.from_euler("ZY", [yaw_deg, pitch_down_deg], degrees=True)   # FLU: +pitch about y = nose down
    xf = UsdGeom.Xformable(zed)
    xf.ClearXformOpOrder()
    xf.AddTranslateOp().Set(Gf.Vec3d(*[float(v) for v in pos]))
    x, y, z, w = rot.as_quat()
    xf.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(float(w), Gf.Vec3d(float(x), float(y), float(z))))


cx, cy = [float(v) for v in a.center.split(",")]
views = []
for h in [float(v) for v in a.heights.split(",")]:
    for k in range(a.yaws):
        yaw = 360.0 * k / a.yaws
        views.append({"pos": [cx + a.radius * np.cos(np.radians(yaw)), cy + a.radius * np.sin(np.radians(yaw)), h],
                      "yaw_deg": yaw, "pitch_down_deg": 15.0 if k % 2 else 0.0})        # looking outward
views += [dict(v, revisit=True) for v in views[:a.revisit]]
set_pose(views[0]["pos"], views[0]["yaw_deg"], views[0]["pitch_down_deg"])

keys = og.Controller.Keys
og.Controller.edit({"graph_path": "/World/zed_stream", "evaluator_name": "execution"}, {
    keys.CREATE_NODES: [("tick", "omni.graph.action.OnPlaybackTick"), ("zed", "sl.sensor.camera.ZED_Camera")],
    keys.CONNECT: [("tick.outputs:tick", "zed.inputs:execIn")],
    keys.SET_VALUES: [("zed.inputs:cameraModel", "ZED_M"), ("zed.inputs:resolution", "HD720"), ("zed.inputs:fps", 30),
                      ("zed.inputs:streamingPort", stream_port(0)), ("zed.inputs:transportLayerMode", "IPC")]})
set_targets(prim=stage.GetPrimAtPath("/World/zed_stream/zed"), attribute="inputs:cameraPrim",
            target_prim_paths=[zed_path])

rp = rep.create.render_product(left, (1280, 720))
gt_annot = rep.AnnotatorRegistry.get_annotator("distance_to_image_plane")
gt_annot.attach([rp])
cam = UsdGeom.Camera(stage.GetPrimAtPath(left))


def intrinsics():
    """The extension authors the ZED_M optics on the camera prims once it streams: read them then, not at load."""
    i = {"focal_mm": cam.GetFocalLengthAttr().Get(), "h_aperture_mm": cam.GetHorizontalApertureAttr().Get(),
         "v_aperture_mm": cam.GetVerticalApertureAttr().Get()}
    i["fx_px"] = i["focal_mm"] / i["h_aperture_mm"] * 1280
    return i


log(f"left camera intrinsics at load {intrinsics()}")

omni.timeline.get_timeline_interface().play()
print("[launch] sim ready (zed pool probe)", flush=True)     # what ./bisg's helpers look for
log(f"streaming on port {stream_port(0)}; waiting for {a.out}/go (start the wrapper + collector, then touch it)")
t_end = time.time() + a.go_timeout
while not os.path.exists(os.path.join(a.out, "go")):
    app.update()
    if time.time() > t_end:
        raise SystemExit("[zprobe] no go file: wrapper never confirmed")

intr = intrinsics()
log(f"left camera intrinsics while streaming {intr}")
t0 = time.time()
for i, v in enumerate(views):
    set_pose(v["pos"], v["yaw_deg"], v["pitch_down_deg"])
    v["t_teleport"] = time.time()
    v["t_frames"] = []
    for f in range(a.dwell):
        app.update()
        v["t_frames"].append(time.time())
        if f == 2:
            early = np.array(gt_annot.get_data(), dtype=np.float32)
    gt = np.array(gt_annot.get_data(), dtype=np.float32)
    v["gt_changed_after_frame2"] = float(np.nanmax(np.abs(np.nan_to_num(gt - early, posinf=0, neginf=0))))
    np.save(os.path.join(a.out, f"gt_{i:03d}.npy"), gt)
    fps = a.dwell / (v["t_frames"][-1] - v["t_teleport"])
    log(f"view {i:2d}/{len(views)} pos={np.round(v['pos'], 2).tolist()} yaw={v['yaw_deg']:.0f} "
        f"pitch={v['pitch_down_deg']:.0f} render {fps:.1f} fps, gt finite {np.isfinite(gt).mean():.2f}")
t_done = time.time()
with open(os.path.join(a.out, "views.json"), "w") as fh:
    json.dump({"views": views, "intrinsics": intr, "dwell": a.dwell, "world": a.world, "camera_prim": left,
               "t_start": t0, "t_done": t_done}, fh)
log(f"done: {len(views)} views in {t_done - t0:.1f} s -> {a.out}")
for _ in range(30):                                   # keep streaming a moment so the collector sees the last view settle
    app.update()
app.close()
