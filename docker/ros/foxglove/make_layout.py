#!/usr/bin/env python3
"""Writes the /drone_1 layouts for the Lichtblick web UI (Foxglove format) next to this file. Stdlib only.

    docker/ros/foxglove/make_layout.py            # then: ./bisg ros restart foxglove, reload the page
    docker/ros/foxglove/make_layout.py OUT_DIR

    raptor.json   the twin itself: flight, every ZED/flow/ToF sensor, VIO debugging
    kinetix.json  Kinetix photogrammetry flights: carrot setpoint vs EKF2 vs truth paths, camera frustum, capture tolerances,
                  drift; only the topics Kinetix consumes (its interfaces.md §4), so it also replays a Kinetix MCAP run bag

FOXGLOVE_LAYOUT (config/bisg.conf) picks the one the printed URL loads. Edit this file, not the JSON. The panel config keys are
Lichtblick 1.29's own (packages/suite-base/src/panels/*/types.ts). Each layout is a Tab panel (the Kinetix one with a status column / strip beside it);
hidden tabs unsubscribe their topics, so the heavy streams only flow while their tab is open.
"""
import json
import os
import sys
from string import Template

D = "/drone_1"
ZED = f"{D}/zed/zed_node"
TITLE = "lichtblickPanelTitle"   # Lichtblick's key for a user-set panel title
cfg = {}                          # configById of the layout being built; write() empties it


def split(a, b, direction="row", pct=50):
    return {"first": a, "second": b, "direction": direction, "splitPercentage": pct}


def image(pid, title, topic, **mode):
    cfg[f"Image!{pid}"] = {TITLE: title, "imageMode": {"imageTopic": topic, **mode}}
    return f"Image!{pid}"


def raw(pid, title, path):
    cfg[f"RawMessages!{pid}"] = {TITLE: title, "topicPath": path, "diffEnabled": False, "diffMethod": "custom",
                                  "diffTopicPath": "", "showFullMessageForDiff": False, "expansion": "all"}
    return f"RawMessages!{pid}"


def plot(pid, title, paths, ylabel):
    cfg[f"Plot!{pid}"] = {TITLE: title, "paths": [
        {"value": v, "label": l, "color": c, "enabled": True, "timestampMethod": "receiveTime"} for v, l, c in paths],
        # legend in its own strip above the plot (one 30 px row per series, colour swatch + label + current value), not floating over the data
        "showLegend": True, "legendDisplay": "top", "showPlotValuesInLegend": True, "showXAxisLabels": True,
        "showYAxisLabels": True, "isSynced": True, "xAxisVal": "timestamp", "followingViewWidth": 30,
        "yAxisLabel": ylabel, "sidebarDimension": 30 * len(paths) + 4}
    return f"Plot!{pid}"


def transitions(pid, title, paths):
    cfg[f"StateTransitions!{pid}"] = {TITLE: title, "isSynced": True, "xAxisRange": 60, "paths": [
        {"value": v, "label": l, "enabled": True, "timestampMethod": "receiveTime"} for v, l in paths]}
    return f"StateTransitions!{pid}"


def grid(frame="odom", size=20):
    return {"grid": {"visible": True, "frameLocked": True, "label": "Grid", "instanceId": "grid", "layerId": "foxglove.Grid",
                     "frameId": frame, "size": size, "divisions": size, "lineWidth": 1, "color": "#248eff40",
                     "position": [0, 0, 0], "rotation": [0, 0, 0], "order": 1}}


def write(name, tree, scripts, out_dir):
    layout = {"configById": dict(cfg), "globalVariables": {}, "userNodes": scripts, "playbackConfig": {"speed": 1.0},
              "layout": tree}
    path = os.path.join(out_dir, f"{name}.json")
    with open(path, "w") as f:
        json.dump(layout, f, indent=2)
        f.write("\n")
    print(f"{path}: {len(cfg)} panels, {len(scripts)} user scripts")
    cfg.clear()


# --- User scripts (run in the browser): Lichtblick draws 32FC1 images as grey 0..1 and ignores colormap/min/max; 16UC1 gets them ---
def f32_to_u16(name, topic, out, scale, what):
    return {"name": name, "sourceCode": f"""// {what}
// Lichtblick draws 32FC1 images as grey 0..1 and ignores colormap/min/max; 16UC1 images get them.
import {{ Input, Message }} from "./types";

type Image = Message<"sensor_msgs/msg/Image">;

export const inputs = ["{topic}"];
export const output = "{out}";

export default function script(event: Input<"{topic}">): Image {{
  const src = event.message;
  const dv = new DataView(src.data.buffer, src.data.byteOffset, src.data.byteLength);
  const le = src.is_bigendian === 0;
  const out = new Uint8Array(src.width * src.height * 2);
  const ov = new DataView(out.buffer);
  for (let r = 0; r < src.height; r++) {{
    for (let c = 0; c < src.width; c++) {{
      const v = dv.getFloat32(r * src.step + c * 4, le);
      const u = Number.isFinite(v) ? Math.min(65535, Math.max(0, Math.round(v * {scale}))) : 0;
      ov.setUint16((r * src.width + c) * 2, u, true);
    }}
  }}
  return {{ header: src.header, height: src.height, width: src.width, encoding: "16UC1", is_bigendian: 0, step: src.width * 2, data: out }};
}}
"""}


DEPTH_SCRIPTS = {
    "depth-mm": f32_to_u16("depth_mm", f"{ZED}/depth/depth_registered", "/studio_script/depth_mm", 1000,
                           "ZED depth [m, 32FC1] -> millimetres [16UC1], NaN/inf -> 0"),
    "confidence-u16": f32_to_u16("confidence_u16", f"{ZED}/confidence/confidence_map", "/studio_script/confidence_u16", 100,
                                 "ZED depth confidence [0-100, 32FC1, higher = less confident] -> x100 [16UC1]"),
}

# Lichtblick 1.29 + foxglove_bridge hand the latched /tf_static only to the 3D panels mounted when it arrives: a 3D panel that mounts
# later (tab switch) has no static frames, so base_link, the grid and the ZED cloud have no transform and it draws nothing (checked
# 2026-10-20). This script keeps the static transforms (its state survives tab switches) and re-sends them with every /tf message,
# restamped with that message's stamp, so every 3D panel gets them as soon as it mounts. Every layout with a 3D panel needs it.
TF_STATIC_REPEAT = {"name": "tf_static_repeat", "sourceCode": """// /tf_static, cached and re-sent with every /tf message (restamped) for 3D panels that mount after it arrived (tab switch)
import { Input, Message } from "./types";

type TF = Message<"tf2_msgs/msg/TFMessage">;
type Transform = TF["transforms"][number];

export const inputs = ["/tf_static", "/tf"];
export const output = "/studio_script/tf_static_repeat";

const statics = new Map<string, Transform>();

// Every call returns the whole set (about 10 transforms): a panel that samples only the newest message per frame still gets all of
// them, and Lichtblick raises "did not produce a message" whenever a script returns nothing.
export default function script(event: Input<"/tf_static"> | Input<"/tf">): TF {
  const m = event.message;
  if (event.topic === "/tf_static") for (const t of m.transforms) statics.set(t.child_frame_id, t);
  const stamp = event.topic === "/tf" && m.transforms.length > 0 ? m.transforms[0].header.stamp : undefined;
  return { transforms: [...statics.values()].map((t) => (stamp ? { ...t, header: { ...t.header, stamp } } : t)) };
}
"""}

# PX4's MAVLink STATUSTEXT (preflight failures, mode changes, EKF2 messages) as rcl_interfaces/Log, so the Log panel shows it with
# severities. Not latched: only what arrives after the page opened (the full history is in /rosout as "FCU: ..." lines).
MAVLINK_LOG = {"name": "mavlink_log", "sourceCode": f"""// mavros/statustext/recv (MAVLink STATUSTEXT from PX4) -> rcl_interfaces/msg/Log for the Log panel
import {{ Input, Message }} from "./types";

type Log = Message<"rcl_interfaces/msg/Log">;

export const inputs = ["{D}/mavros/statustext/recv"];
export const output = "/studio_script/mavlink_log";

// MAVLink severity 0 EMERGENCY .. 7 DEBUG -> ROS 2 FATAL 50 / ERROR 40 / WARN 30 / INFO 20 / DEBUG 10
const LEVEL = [50, 50, 50, 40, 30, 20, 20, 10];

export default function script(event: Input<"{D}/mavros/statustext/recv">): Log {{
  const m = event.message;
  return {{ stamp: m.header.stamp, level: LEVEL[m.severity] ?? 20, name: "PX4", msg: m.text, file: "", function: "", line: 0 }};
}}
"""}


def raptor():
    # --- Flight tab --------------------------------------------------------------------------------------------------------------
    cfg["3D!flight"] = {
        TITLE: "3D (follows base_link)", "followTf": "base_link", "followMode": "follow-position",
        "cameraState": {"distance": 6, "perspective": True, "phi": 60, "thetaOffset": 45, "targetOffset": [0, 0, 0], "fovy": 45,
                        "near": 0.05, "far": 500},
        "scene": {"transforms": {"showLabel": False, "axisScale": 0.6, "lineWidth": 1}, "backgroundColor": "#15171c"},
        "transforms": {"frame:odom": {"visible": True}, "frame:base_link": {"visible": True}, "frame:map": {"visible": False}},
        "topics": {
            f"{ZED}/odom": {"visible": True, "type": "arrow", "color": "#3fb950ff", "arrowScale": [0.8, 0.12, 0.12]},
            f"{D}/mavros/local_position/pose": {"visible": True, "type": "arrow", "color": "#58a6ffff", "arrowScale": [0.8, 0.12, 0.12]},
            f"{D}/state/pose": {"visible": True, "type": "axis", "axisScale": 0.5},
            f"{ZED}/point_cloud/cloud_registered": {"visible": False, "pointSize": 2, "colorMode": "rgb", "colorField": "rgb", "decayTime": 0},
            # ZED spatial mapping (zed.yaml spatial_mapping.enabled): the whole fused map, already accumulated by the SDK, 1 Hz
            f"{ZED}/mapping/fused_cloud": {"visible": True, "pointSize": 2, "colorMode": "rgb", "colorField": "rgb", "decayTime": 0},
        },
        "layers": grid(),
    }
    alt = plot("altitude", "Altitude z [m]: EKF2 vs ZED vs ground truth vs ToF", [
        (f"{D}/mavros/local_position/pose.pose.position.z", "EKF2 (mavros)", "#58a6ff"),
        (f"{ZED}/odom.pose.pose.position.z", "ZED odom", "#3fb950"),
        (f"{D}/state/pose.pose.position.z", "ground truth (world frame)", "#e6edf3"),
        (f"{D}/mavros/hrlv_ez4_pub{{range<40}}.range", "ToF range (valid only)", "#d29922")], "m")   # range >= max_range (100) = no reading
    xy = plot("xy", "Position x / y [m]: EKF2 (from takeoff) vs ground truth (world)", [
        (f"{D}/mavros/local_position/pose.pose.position.x", "EKF2 x", "#58a6ff"),
        (f"{D}/state/pose.pose.position.x", "truth x (world)", "#a5d6ff"),
        (f"{D}/mavros/local_position/pose.pose.position.y", "EKF2 y", "#f78166"),
        (f"{D}/state/pose.pose.position.y", "truth y (world)", "#ffc8b8")], "m")
    flight = split("3D!flight", split(alt, xy, "row", 50), "column", 64)

    # --- Camera tab (the heavy topics): the QGC picture's 2x2, left | chase / depth | confidence (docker/zed/zed_stack/mosaic.py) ----
    cam_left = image("camleft", "ZED left (raw)", f"{ZED}/left/color/rect/image")
    chase = image("chase", "Chase cam (sim only)", f"{D}/chase/image")
    depth = image("depth", "ZED depth [0.3-10 m, turbo; script depth_mm]", "/studio_script/depth_mm",
                  colorMode="colormap", colorMap="turbo", minValue=300, maxValue=10000)
    conf = image("confidence", "Depth confidence [blue good - red bad; script confidence_u16]", "/studio_script/confidence_u16",
                 colorMode="colormap", colorMap="turbo", minValue=0, maxValue=10000)
    camera = split(split(cam_left, chase, "row", 50), split(depth, conf, "row", 50), "column", 50)

    # --- Sensors tab: plots only (FC IMU / gyro, ZED IMU, down range, flow, barometer) -----------------------------
    accel = plot("imu", "FC IMU acceleration [m/s^2]", [
        (f"{D}/mavros/imu/data.linear_acceleration.x", "accel x", "#f85149"),
        (f"{D}/mavros/imu/data.linear_acceleration.y", "accel y", "#3fb950"),
        (f"{D}/mavros/imu/data.linear_acceleration.z", "accel z", "#58a6ff")], "m/s^2")
    gyro = plot("gyro", "FC gyro [rad/s]", [
        (f"{D}/mavros/imu/data.angular_velocity.x", "roll rate (x)", "#f85149"),
        (f"{D}/mavros/imu/data.angular_velocity.y", "pitch rate (y)", "#3fb950"),
        (f"{D}/mavros/imu/data.angular_velocity.z", "yaw rate (z)", "#58a6ff")], "rad/s")
    zed_imu = plot("zedimu", "ZED IMU acceleration [m/s^2] (camera frame)", [
        (f"{ZED}/imu/data.linear_acceleration.x", "accel x", "#f85149"),
        (f"{ZED}/imu/data.linear_acceleration.y", "accel y", "#3fb950"),
        (f"{ZED}/imu/data.linear_acceleration.z", "accel z", "#58a6ff")], "m/s^2")
    rng = plot("range", "Down range [m]: ToF vs flow distance", [
        (f"{D}/mavros/hrlv_ez4_pub{{range<40}}.range", "ToF range (LW20)", "#d29922"),
        (f"{D}/mavros/px4flow/ground_distance{{range>0}}.range", "flow distance (PMW3901)", "#a5d6ff")], "m")
    flow_plot = plot("flowplot", "PMW3901 flow [rad per sample] (forward = -y, left = +x)", [
        (f"{D}/mavros/px4flow/raw/optical_flow_rad.integrated_x", "flow x (left +)", "#f85149"),
        (f"{D}/mavros/px4flow/raw/optical_flow_rad.integrated_y", "flow y (forward -)", "#3fb950")], "rad")
    baro = plot("baro", "Barometer [Pa] (EKF2 height reference)", [
        (f"{D}/mavros/imu/static_pressure.fluid_pressure", "static pressure (EKF2 height ref)", "#d2a8ff")], "Pa")
    cfg["RosOut!mavlink"] = {TITLE: "MAVLink log (PX4 STATUSTEXT; script mavlink_log)", "searchTerms": [], "minLogLevel": 1,
                             "topicToRender": "/studio_script/mavlink_log"}
    sensors = split(split(accel, gyro, "row", 50), split(split(zed_imu, rng, "row", 50), split(flow_plot, baro, "row", 50), "column", 50),
                    "column", 33)

    # --- Debug tab ---------------------------------------------------------------------------------------------------------------
    cfg["RosOut!log"] = {TITLE: "Log (/rosout)", "searchTerms": [], "minLogLevel": 2, "topicToRender": "/rosout"}
    cfg["TopicGraph!graph"] = {TITLE: "Topic graph"}   # no stored settings (orientation / topic filter are toolbar state): own full-size tab
    debug = split("RosOut!log", "RosOut!mavlink", "column", 50)

    cfg["Tab!main"] = {"activeTabIdx": 0, "tabs": [
        {"title": "Flight", "layout": flight}, {"title": "Sensors", "layout": sensors}, {"title": "Camera", "layout": camera},
        {"title": "Debug", "layout": debug}, {"title": "Graph", "layout": "TopicGraph!graph"}]}
    return "Tab!main", {**DEPTH_SCRIPTS, "mavlink-log": MAVLINK_LOG, "tf-static-repeat": TF_STATIC_REPEAT}


# --- Kinetix ------------------------------------------------------------------------------------------------------------------------
# Kinetix (~/Documents/github/kinetix) flies room/object photogrammetry through MAVROS: it streams a carrot on
# mavros/setpoint_position/local, reads mavros/local_position/pose (EKF2) and grabs the ZED left image; state/pose (sim truth) is
# for evaluation only. Its capture tolerances (kinetix config/default.yaml, rig:), mirrored here for the "in tolerance" display:
TOL_POS_M, TOL_YAW_DEG, TOL_SPEED_MPS = 0.10, 3.0, 0.05
POSE, SETPOINT, TRUTH, STATE = (f"{D}/mavros/local_position/pose", f"{D}/mavros/setpoint_position/local", f"{D}/state/pose",
                                f"{D}/mavros/state")
LEFT_INFO = f"{ZED}/left/color/rect/camera_info"

TS_COMMON = """import { Input, Message } from "./types";

type Vec = [number, number, number];
type PoseStamped = Message<"geometry_msgs/msg/PoseStamped">;
const vec = (p: { x: number; y: number; z: number }): Vec => [p.x, p.y, p.z];
const dist = (a: Vec, b: Vec): number => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
const secs = (t: { sec: number; nsec: number }): number => t.sec + t.nsec * 1e-9;
"""

# map - world offset (EKF2 minus truth) measured while disarmed, like Kinetix's auto_world_to_map; latched in the air when the page
# opened mid-flight (drift then counts from that moment). Shared by the truth path and the flight summary.
TS_OFFSET = """let ekf: Vec | undefined, truth: Vec | undefined, off: Vec | undefined, offFrom = "none", armed = false;
function measureOffset(): void {
  if (!ekf || !truth) return;
  if (!armed) { off = [ekf[0] - truth[0], ekf[1] - truth[1], ekf[2] - truth[2]]; offFrom = "ground"; }
  else if (!off) { off = [ekf[0] - truth[0], ekf[1] - truth[1], ekf[2] - truth[2]]; offFrom = "air"; }
}
"""


def ts(name, what, body, **subs):
    src = f"// {what}\n" + TS_COMMON + Template(body).substitute(STATE=STATE, **subs)
    return {"name": name, "sourceCode": src}


def path_script(name, what, src, out):
    """nav_msgs/Path of `src` (a PoseStamped in map), one point per 5 cm, restarted when the vehicle arms."""
    return ts(name, what, """
type Path = Message<"nav_msgs/msg/Path">;

export const inputs = ["$SRC", "$STATE"];
export const output = "$OUT";
const STEP_M = 0.05;       // one point every 5 cm
const MAX_POINTS = 8000;   // 400 m

let poses: PoseStamped[] = [];
let armed = false;
let out: Path = { header: { stamp: { sec: 0, nsec: 0 }, frame_id: "map" }, poses: [] };   // returned unchanged between points

export default function script(event: Input<"$SRC"> | Input<"$STATE">): Path {
  if (event.topic === "$STATE") {
    if (event.message.armed && !armed) { poses = []; out = { header: out.header, poses: [] }; }   // a new flight starts a new path
    armed = event.message.armed;
    return out;
  }
  const m = event.message;
  const last = poses[poses.length - 1];
  if (last && dist(vec(last.pose.position), vec(m.pose.position)) < STEP_M) return out;
  poses.push(m);
  if (poses.length > MAX_POINTS) poses.shift();
  out = { header: { stamp: m.header.stamp, frame_id: "map" }, poses: poses.slice() };
  return out;
}
""", SRC=src, OUT=out)


KINETIX_SCRIPTS = {
    "path-ekf2": path_script("path_ekf2", "Flown path: EKF2 (mavros/local_position/pose), map", POSE, "/studio_script/path_ekf2"),
    "path-setpoint": path_script("path_setpoint", "Commanded path: the carrot Kinetix streams (mavros/setpoint_position/local), map",
                                 SETPOINT, "/studio_script/path_setpoint"),
    "path-truth": ts("path_truth", "True path (sim state/pose, world) moved into map by the measured map - world offset", """
type Path = Message<"nav_msgs/msg/Path">;

export const inputs = ["$TRUTH", "$POSE", "$STATE"];
export const output = "/studio_script/path_truth";
const STEP_M = 0.05, MAX_POINTS = 8000;
""" + TS_OFFSET + """
let poses: PoseStamped[] = [];
let out: Path = { header: { stamp: { sec: 0, nsec: 0 }, frame_id: "map" }, poses: [] };   // returned unchanged between points

export default function script(event: Input<"$TRUTH"> | Input<"$POSE"> | Input<"$STATE">): Path {
  if (event.topic === "$STATE") {
    if (event.message.armed && !armed) { poses = []; out = { header: out.header, poses: [] }; }
    armed = event.message.armed;
    return out;
  }
  if (event.topic === "$POSE") { ekf = vec(event.message.pose.position); measureOffset(); return out; }
  const m = event.message;
  truth = vec(m.pose.position);
  measureOffset();
  if (!off) return out;
  const p = { x: truth[0] + off[0], y: truth[1] + off[1], z: truth[2] + off[2] };
  const last = poses[poses.length - 1];
  if (last && dist(vec(last.pose.position), vec(p)) < STEP_M) return out;
  poses.push({ header: { stamp: m.header.stamp, frame_id: "map" }, pose: { position: p, orientation: m.pose.orientation } });
  if (poses.length > MAX_POINTS) poses.shift();
  out = { header: { stamp: m.header.stamp, frame_id: "map" }, poses: poses.slice() };
  return out;
}
""", TRUTH=TRUTH, POSE=POSE),
    "kinetix-track": ts("kinetix_track", "Setpoint tracking against Kinetix's capture tolerances", """
// in_tol = distance, yaw error and speed all inside the tolerances now; settled_s = seconds (EKF2 stamps) in tolerance without a
// break: Kinetix grabs its image once that reaches settle_s (1 s). setpoint_age_s > 0.5 = no setpoint stream (nobody in OFFBOARD).
// Speed = EKF2 position differences (smoothed), so this also works on a Kinetix run bag (it has no velocity topic).
type Track = {
  dist_m: number; dist_xy_m: number; dz_m: number; yaw_err_deg: number; speed_mps: number;
  in_tol: boolean; settled_s: number; setpoint_age_s: number;
};

export const inputs = ["$POSE", "$SETPOINT"];
export const output = "/studio_script/kinetix_track";
const TOL_POS_M = $TOL_POS, TOL_YAW_DEG = $TOL_YAW, TOL_SPEED_MPS = $TOL_SPEED;

const yaw = (q: { x: number; y: number; z: number; w: number }): number =>
  Math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z));
let sp: { p: Vec; yaw: number; rx: number } | undefined;
let prev: { t: number; p: Vec } | undefined;
let speed = 0;
let tolSince: number | undefined;
let out: Track = { dist_m: NaN, dist_xy_m: NaN, dz_m: NaN, yaw_err_deg: NaN, speed_mps: NaN, in_tol: false, settled_s: 0, setpoint_age_s: NaN };

export default function script(event: Input<"$POSE"> | Input<"$SETPOINT">): Track {
  const m = event.message;
  if (event.topic === "$SETPOINT") {
    sp = { p: vec(m.pose.position), yaw: yaw(m.pose.orientation), rx: secs(event.receiveTime) };
    return out;   // the last result again: a script that returns nothing raises a Lichtblick alert
  }
  const t = secs(m.header.stamp), p = vec(m.pose.position);
  if (prev && t > prev.t) speed = 0.7 * speed + 0.3 * dist(p, prev.p) / (t - prev.t);
  else if (prev && t < prev.t) speed = 0;   // time went back (sim restart, bag loop)
  prev = { t, p };
  if (!sp) {
    out = { dist_m: NaN, dist_xy_m: NaN, dz_m: NaN, yaw_err_deg: NaN, speed_mps: speed, in_tol: false, settled_s: 0, setpoint_age_s: NaN };
    return out;
  }
  const d = dist(p, sp.p), dxy = Math.hypot(p[0] - sp.p[0], p[1] - sp.p[1]), dz = p[2] - sp.p[2];
  let dyaw = yaw(m.pose.orientation) - sp.yaw;
  dyaw = Math.abs(Math.atan2(Math.sin(dyaw), Math.cos(dyaw))) * 180 / Math.PI;
  const age = secs(event.receiveTime) - sp.rx;
  const inTol = age < 0.5 && d < TOL_POS_M && dyaw < TOL_YAW_DEG && speed < TOL_SPEED_MPS;
  if (!inTol) tolSince = undefined;
  else if (tolSince === undefined) tolSince = t;
  out = { dist_m: d, dist_xy_m: dxy, dz_m: dz, yaw_err_deg: dyaw, speed_mps: speed, in_tol: inTol,
          settled_s: tolSince === undefined ? 0 : t - tolSince, setpoint_age_s: age };
  return out;
}
""", POSE=POSE, SETPOINT=SETPOINT, TOL_POS=TOL_POS_M, TOL_YAW=TOL_YAW_DEG, TOL_SPEED=TOL_SPEED_MPS),
    "kinetix-flight": ts("kinetix_flight", "Flight summary: time and distance since arming, EKF2 drift against the sim truth", """
// Drift = EKF2 - (truth + map-world offset); NaN without truth (real drone, a bag without state/pose). Values freeze at landing
// and reset at the next arming.
type Summary = {
  flight_s: number; odometer_m: number; drift_m: number; drift_xy_m: number; drift_z_m: number; max_drift_m: number;
  offset_from: string;
};

export const inputs = ["$POSE", "$TRUTH", "$STATE"];
export const output = "/studio_script/kinetix_flight";
""" + TS_OFFSET + """
let armedAt: number | undefined, last: Vec | undefined, flight = 0, odo = 0, maxDrift = 0;
let out: Summary = { flight_s: 0, odometer_m: 0, drift_m: NaN, drift_xy_m: NaN, drift_z_m: NaN, max_drift_m: 0, offset_from: "none" };

export default function script(event: Input<"$POSE"> | Input<"$TRUTH"> | Input<"$STATE">): Summary {
  if (event.topic === "$STATE") {
    if (event.message.armed && !armed) { armedAt = undefined; last = undefined; flight = 0; odo = 0; maxDrift = 0; }
    armed = event.message.armed;
    return out;   // the last result again: a script that returns nothing raises a Lichtblick alert
  }
  if (event.topic === "$TRUTH") { truth = vec(event.message.pose.position); measureOffset(); return out; }
  const t = secs(event.message.header.stamp), p = vec(event.message.pose.position);
  ekf = p;
  measureOffset();
  if (armed) {
    if (armedAt === undefined) armedAt = t;
    flight = t - armedAt;
    if (last) odo += dist(p, last);
    last = p;
  }
  const e: Vec = truth && off ? [p[0] - truth[0] - off[0], p[1] - truth[1] - off[1], p[2] - truth[2] - off[2]] : [NaN, NaN, NaN];
  const drift = Math.hypot(e[0], e[1], e[2]);
  if (armed && Number.isFinite(drift)) maxDrift = Math.max(maxDrift, drift);
  out = { flight_s: flight, odometer_m: odo, drift_m: drift, drift_xy_m: Math.hypot(e[0], e[1]), drift_z_m: e[2],
          max_drift_m: maxDrift, offset_from: offFrom };
  return out;
}
""", POSE=POSE, TRUTH=TRUTH),
    **DEPTH_SCRIPTS,
    "tf-static-repeat": TF_STATIC_REPEAT,
}


def kinetix():
    track, summary = "/studio_script/kinetix_track", "/studio_script/kinetix_flight"

    # --- Status column -----------------------------------------------------------------------------------------------------------
    status = transitions("status", "Mode / armed / FCU link / capture tolerance", [
        (f"{STATE}.mode", "mode"), (f"{STATE}.armed", "armed"), (f"{STATE}.connected", "FCU link"),
        (f"{track}.in_tol", f"in tolerance ({TOL_POS_M:g} m, {TOL_YAW_DEG:g} deg, {TOL_SPEED_MPS:g} m/s)")])
    flight_sum = raw("flight", "Flight: time, distance, drift (script kinetix_flight)", summary)
    battery = raw("battery", "Battery (0-1)", f"{D}/mavros/battery.percentage")
    zed_health = raw("zedstatus", "ZED stack health (camera loss aborts Kinetix)", f"{D}/zed_stack/status.data")
    status_col = split(status, flight_sum, "column", 45)
    status_strip = split(battery, zed_health, "row", 15)   # thin bottom strip under the tabs

    # --- Flight tab: where the drone is, where it is told to be, what it sees ----------------------------------------------------
    hidden = ["map_ned", "odom_ned", "base_link_frd", "hrlv_ez4_sonar", "zed_camera_link", "zed_camera_center", "zed_imu_link",
              "zed_left_camera_frame", "zed_right_camera_frame", "zed_right_camera_frame_optical", "zed_left_camera_frame_optical"]
    cfg["3D!flight"] = {
        TITLE: "3D: EKF2 path (blue), carrot setpoint (orange), truth (white), ZED left frustum",
        "followTf": "base_link", "followMode": "follow-position",
        "cameraState": {"distance": 12, "perspective": True, "phi": 50, "thetaOffset": 45, "targetOffset": [0, 0, 0], "fovy": 45,
                        "near": 0.05, "far": 500},
        "scene": {"transforms": {"showLabel": False, "axisScale": 0.5, "lineWidth": 1}, "backgroundColor": "#15171c"},
        "transforms": {"frame:base_link": {"visible": True}, "frame:map": {"visible": True},
                       **{f"frame:{f}": {"visible": False} for f in hidden}},
        "topics": {
            "/studio_script/path_ekf2": {"visible": True, "type": "line", "lineWidth": 0.04, "gradient": ["#58a6ffff", "#58a6ffff"]},
            "/studio_script/path_setpoint": {"visible": True, "type": "line", "lineWidth": 0.02, "gradient": ["#f0883eff", "#f0883eff"]},
            "/studio_script/path_truth": {"visible": True, "type": "line", "lineWidth": 0.02, "gradient": ["#e6edf3cc", "#e6edf3cc"]},
            POSE: {"visible": True, "type": "arrow", "color": "#58a6ffff", "arrowScale": [0.6, 0.1, 0.1]},
            SETPOINT: {"visible": True, "type": "arrow", "color": "#f0883eff", "arrowScale": [0.6, 0.1, 0.1]},
            LEFT_INFO: {"visible": True, "distance": 0.6, "width": 1.5, "color": "#d2a8ffff"},
        },
        "layers": grid("map", 30),
    }
    zed_left = image("zedleft", "ZED left: what Kinetix captures (compressed)", f"{ZED}/left/color/rect/image/compressed")
    chase = image("chase", "Chase cam (sim only)", f"{D}/chase/image")
    tracking = plot("tracking", "Tracking: distance to setpoint [m], speed [m/s] (capture needs < 0.10 m, < 0.05 m/s)", [
        (f"{track}.dist_m", "distance to setpoint", "#f0883e"),
        (f"{track}.speed_mps", "speed (motion blur)", "#3fb950"),
        (f"{track}.dz_m", "height error (signed)", "#d2a8ff")], "m, m/s")
    drift = plot("drift", "EKF2 drift vs sim truth [m] (offset measured on the ground)", [
        (f"{summary}.drift_m", "3D", "#f85149"),
        (f"{summary}.drift_xy_m", "horizontal", "#58a6ff"),
        (f"{summary}.drift_z_m", "vertical (signed)", "#d29922")], "m")
    alt = plot("altitude", "Altitude z [m]: EKF2 vs setpoint vs ToF", [
        (f"{POSE}.pose.position.z", "EKF2", "#58a6ff"),
        (f"{SETPOINT}.pose.position.z", "setpoint", "#f0883e"),
        (f"{D}/mavros/hrlv_ez4_pub{{range<40}}.range", "ToF range (valid only)", "#8b949e")], "m")
    flight = split(split("3D!flight", split(zed_left, chase, "column", 62), "row", 58),
                   split(tracking, split(drift, alt, "row", 50), "row", 40), "column", 66)

    # --- Stereo tab: only for Kinetix's stereo comparison modes (stereo_rig*, plan_depth=stereo); heavy, flows only while open ----
    cam_left = image("camleft", "ZED left (raw)", f"{ZED}/left/color/rect/image")
    cam_right = image("camright", "ZED right (raw, stereo_rig*)", f"{ZED}/right/color/rect/image")
    depth = image("depth", "ZED depth [0.3-10 m, turbo] (plan_depth=stereo)", "/studio_script/depth_mm",
                  colorMode="colormap", colorMap="turbo", minValue=300, maxValue=10000)
    conf = image("confidence", "Depth confidence [blue good - red bad] (stereo_zed confidence = 1 - c/100)",
                 "/studio_script/confidence_u16", colorMode="colormap", colorMap="turbo", minValue=0, maxValue=10000)
    stereo = split(split(cam_left, cam_right, "row", 50), split(depth, conf, "row", 50), "column", 50)

    # --- Debug tab ---------------------------------------------------------------------------------------------------------------
    cfg["RosOut!log"] = {TITLE: "Log (/rosout)", "searchTerms": [], "minLogLevel": 2, "topicToRender": "/rosout"}
    track_raw = raw("track", "Tracking (script kinetix_track)", track)
    sp_raw = raw("setpoint", "mavros/setpoint_position/local (the carrot)", SETPOINT)
    fcu_state = raw("fcustate", "mavros/state (full)", STATE)
    info = raw("caminfo", "ZED left camera_info (K, size: never hard-coded in Kinetix)", LEFT_INFO)
    debug = split("RosOut!log", split(split(track_raw, sp_raw, "column", 50), split(fcu_state, info, "column", 40), "column", 50),
                  "row", 45)

    cfg["Tab!main"] = {"activeTabIdx": 0, "tabs": [
        {"title": "Flight", "layout": flight}, {"title": "Stereo", "layout": stereo}, {"title": "Debug", "layout": debug}]}
    return split(split(status_col, "Tab!main", "row", 18), status_strip, "column", 94), KINETIX_SCRIPTS


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    for name, build in (("raptor", raptor), ("kinetix", kinetix)):
        write(name, *build(), out_dir)
