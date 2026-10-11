"""
Raw CAD USD (docker/sim/tools/step_to_usd.py) -> Pegasus-ready vehicle USD. Step 2 of the raptor asset pipeline.

Layout, the one Pegasus' Multirotor needs (same as the stock Iris USD):
  /vehicle (articulation root) / body (rigid body: mass, inertia, CoM at the origin; visual + duct collision proxies)
                               / rotor0..3 (1-2 g rigid bodies at the motors) / joint0..3 (revolute about Z to body)

    docker run --rm --gpus all -e ACCEPT_EULA=Y -e PRIVACY_CONSENT=Y -v $PWD:/workspace -w /workspace \
        --entrypoint /isaac-sim/python.sh bisg/sim:6.0.0 docker/sim/tools/build_raptor.py --out /workspace/docker/sim/cache/raptor_build
then copy <out>/raptor.usd next to raptor.yaml (the container user cannot write docker/sim/assets). Inputs: raptor.yaml.
"""
import argparse
import json
import os

import numpy as np
import yaml

ASSET = "/workspace/docker/sim/assets/vehicles/raptor"
IRIS = "/workspace/docker/sim/PegasusSimulator/extensions/pegasus.simulator/pegasus/simulator/assets/Robots/Iris/iris.usd"

ap = argparse.ArgumentParser()
ap.add_argument("--cfg", default=f"{ASSET}/raptor.yaml")
ap.add_argument("--out", required=True, help="writable output directory")
args = ap.parse_args()
cfg = yaml.safe_load(open(args.cfg))

# --- mass properties from the placeholder groups (boxes + parallel axis), CAD-FLU ----------------------------------------
groups = cfg["mass_groups"]
M = sum(g["mass"] for g in groups)
com = sum(g["mass"] * np.array(g["centre"], float) for g in groups) / M
I = np.zeros(3)
for g in groups:
    m, (a, b, c), d = g["mass"], g["size"], np.array(g["centre"], float) - com
    own = m / 12.0 * np.array([b * b + c * c, a * a + c * c, a * a + b * b])
    I += own + m * np.array([d[1] ** 2 + d[2] ** 2, d[0] ** 2 + d[2] ** 2, d[0] ** 2 + d[1] ** 2])
print(f"[build] mass {M:.3f} kg  CoM(CAD-FLU) {com.round(4).tolist()}  I_diag {I.round(6).tolist()}")

from isaacsim import SimulationApp  # noqa: E402

app = SimulationApp({"headless": True})

from pxr import Gf, PhysxSchema, Sdf, Usd, UsdGeom, UsdPhysics  # noqa: E402

os.makedirs(args.out, exist_ok=True)
out_path = os.path.join(args.out, "raptor.usd")
stage = Usd.Stage.CreateNew(out_path)
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
UsdGeom.SetStageMetersPerUnit(stage, 1.0)
UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)

root = UsdGeom.Xform.Define(stage, "/vehicle")
stage.SetDefaultPrim(root.GetPrim())
UsdPhysics.ArticulationRootAPI.Apply(root.GetPrim())
art = PhysxSchema.PhysxArticulationAPI.Apply(root.GetPrim())
art.CreateEnabledSelfCollisionsAttr(False)


def rel(p):
    """CAD-FLU point -> body frame (origin at the centre of mass)."""
    return Gf.Vec3d(*(np.array(p, float) - com))


# --- body: rigid body copying the Iris' PhysX rigid-body settings ------------------------------------------------------
body = UsdGeom.Xform.Define(stage, "/vehicle/body")
bp = body.GetPrim()
UsdPhysics.RigidBodyAPI.Apply(bp)
PhysxSchema.PhysxRigidBodyAPI.Apply(bp)
iris = Usd.Stage.Open(IRIS)
for a in iris.GetPrimAtPath("/vehicle/body").GetAttributes():
    if a.GetName().startswith("physxRigidBody:") and a.HasAuthoredValue():
        bp.CreateAttribute(a.GetName(), a.GetTypeName()).Set(a.Get())
mass = UsdPhysics.MassAPI.Apply(bp)
mass.CreateMassAttr(float(M))
mass.CreateDiagonalInertiaAttr(Gf.Vec3f(*[float(x) for x in I]))
mass.CreateCenterOfMassAttr(Gf.Vec3f(0, 0, 0))
mass.CreatePrincipalAxesAttr(Gf.Quatf(1, 0, 0, 0))

# visual: the CAD, rotated into FLU and shifted so the CoM is the body origin; excluded parts deactivated
vis = UsdGeom.Xform.Define(stage, "/vehicle/body/visual")
vis.AddTranslateOp().Set(Gf.Vec3d(*(-com)))
vis.AddRotateZOp().Set(float(cfg["cad"]["rotate_z_deg"]))
raw = Usd.Stage.Open(os.path.join(ASSET, cfg["cad"]["raw_usd"]))
raw_root = raw.GetDefaultPrim().GetPath() if raw.GetDefaultPrim() else raw.GetPseudoRoot().GetChildren()[0].GetPath()
vis.GetPrim().GetReferences().AddReference("./" + cfg["cad"]["raw_usd"], raw_root)
dropped = []
for p in Usd.PrimRange(raw.GetPrimAtPath(raw_root)):
    if any(s in p.GetName() for s in cfg["cad"]["exclude"]) and p.GetParent().GetName() == "Setup":
        rel_path = str(p.GetPath())[len(str(raw_root)):]
        stage.OverridePrim("/vehicle/body/visual" + rel_path).SetActive(False)
        dropped.append(p.GetName())
print(f"[build] visual from {raw_root}; dropped {dropped}")

# collision: one solid cylinder per duct, invisible (purpose=guide)
col = cfg["collision"]
zc, h = 0.5 * (col["z_bottom"] + col["z_top"]), col["z_top"] - col["z_bottom"]
UsdGeom.Xform.Define(stage, "/vehicle/body/collision")
for i, (fx, fy) in enumerate(cfg["motors"]["positions"]):
    cyl = UsdGeom.Cylinder.Define(stage, f"/vehicle/body/collision/duct{i}")
    cyl.CreateAxisAttr("Z")
    cyl.CreateRadiusAttr(float(col["duct_radius"]))
    cyl.CreateHeightAttr(float(h))
    cyl.AddTranslateOp().Set(rel([fx, fy, zc]))
    cyl.GetPurposeAttr().Set(UsdGeom.Tokens.guide)
    UsdPhysics.CollisionAPI.Apply(cyl.GetPrim())

# --- rotors + revolute joints --------------------------------------------------------------------------------------------
rz = cfg["motors"]["z"]
for i, (fx, fy) in enumerate(cfg["motors"]["positions"]):
    pos = rel([fx, fy, rz])
    r = UsdGeom.Xform.Define(stage, f"/vehicle/rotor{i}")
    r.AddTranslateOp().Set(pos)
    UsdPhysics.RigidBodyAPI.Apply(r.GetPrim())
    PhysxSchema.PhysxRigidBodyAPI.Apply(r.GetPrim())
    rm = UsdPhysics.MassAPI.Apply(r.GetPrim())
    rm.CreateMassAttr(float(cfg["motors"]["rotor_mass"]))
    rm.CreateDiagonalInertiaAttr(Gf.Vec3f(1e-7, 1e-7, 2e-7))
    j = UsdPhysics.RevoluteJoint.Define(stage, f"/vehicle/rotor{i}/joint{i}")
    j.CreateBody0Rel().SetTargets([Sdf.Path("/vehicle/body")])
    j.CreateBody1Rel().SetTargets([Sdf.Path(f"/vehicle/rotor{i}")])
    j.CreateLocalPos0Attr().Set(Gf.Vec3f(*pos))
    j.CreateLocalPos1Attr().Set(Gf.Vec3f(0, 0, 0))
    j.CreateLocalRot0Attr().Set(Gf.Quatf(1, 0, 0, 0))
    j.CreateLocalRot1Attr().Set(Gf.Quatf(1, 0, 0, 0))
    j.CreateAxisAttr("Z")

stage.GetRootLayer().Save()

# --- numbers for the scenario ------------------------------------------------------------------------------------------
bottom = com[2] - col["z_bottom"]
s = cfg["sensors"]
summary = {
    "mass_kg": round(M, 4), "com_cad_flu": com.round(4).tolist(), "inertia_diag": I.round(6).tolist(),
    "rest_height_m": round(float(bottom), 4),
    "zed_mount_xyz": (np.array(s["zed_camera_link"]) - com).round(4).tolist(),
    "tof_mount_xyz": (np.array(s["tof"]) - com).round(4).tolist(),
    "motors_body_xy": [(np.array(p) - com[:2]).round(4).tolist() for p in cfg["motors"]["positions"]],
}
json.dump(summary, open(os.path.join(args.out, "raptor_summary.json"), "w"), indent=1)
print("[build] summary", json.dumps(summary))
print(f"[build] wrote {out_path}")
app.close()
