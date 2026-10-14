#!/usr/bin/env python3
"""Writes raptor.json (next to this file): the /drone_1 layout for the Lichtblick web UI (Foxglove format). Stdlib only.

    docker/ros/foxglove/make_layout.py            # then: ./bisg ros restart foxglove, reload the page
    docker/ros/foxglove/make_layout.py OUT.json

Edit this file, not raptor.json. The panel config keys are Lichtblick 1.29's own (packages/suite-base/src/panels/*/types.ts).
Layout: a status column (always visible) + a Tab panel: Flight | Camera | Debug. Hidden tabs unsubscribe their topics, so the
heavy streams (raw left image, depth, point cloud: ~100 MB/s together) only flow while the Camera tab is open.
"""
import json
import os
import sys

D = "/drone_1"
ZED = f"{D}/zed/zed_node"
TITLE = "lichtblickPanelTitle"   # Lichtblick's key for a user-set panel title
cfg = {}


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
        "showLegend": True, "legendDisplay": "floating", "showPlotValuesInLegend": True, "showXAxisLabels": True,
        "showYAxisLabels": True, "isSynced": True, "xAxisVal": "timestamp", "followingViewWidth": 30,
        "yAxisLabel": ylabel, "sidebarDimension": 240}
    return f"Plot!{pid}"


def grid():
    return {"grid": {"visible": True, "frameLocked": True, "label": "Grid", "instanceId": "grid", "layerId": "foxglove.Grid",
                     "frameId": "odom", "size": 20, "divisions": 20, "lineWidth": 1, "color": "#248eff40",
                     "position": [0, 0, 0], "rotation": [0, 0, 0], "order": 1}}


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


USER_SCRIPTS = {
    "depth-mm": f32_to_u16("depth_mm", f"{ZED}/depth/depth_registered", "/studio_script/depth_mm", 1000,
                           "ZED depth [m, 32FC1] -> millimetres [16UC1], NaN/inf -> 0"),
    "confidence-u16": f32_to_u16("confidence_u16", f"{ZED}/confidence/confidence_map", "/studio_script/confidence_u16", 100,
                                 "ZED depth confidence [0-100, 32FC1, higher = less confident] -> x100 [16UC1]"),
}

# --- Status column, outside the Tab panel so it is always visible ---------------------------------------------------------------
# Raw Messages / State Transitions only: in Lichtblick 1.28-1.29 the Indicator and Gauge panels lose their subscription at page load
# when a 3D or Image panel is mounted (they stay "no data"; checked 2026-10-13).
cfg["StateTransitions!status"] = {TITLE: "Mode / armed / FCU link", "isSynced": True, "xAxisRange": 60, "paths": [
    {"value": f"{D}/mavros/state.mode", "label": "mode", "enabled": True, "timestampMethod": "receiveTime"},
    {"value": f"{D}/mavros/state.armed", "label": "armed", "enabled": True, "timestampMethod": "receiveTime"},
    {"value": f"{D}/mavros/state.connected", "label": "FCU link", "enabled": True, "timestampMethod": "receiveTime"}]}
battery = raw("battery", "Battery (0-1)", f"{D}/mavros/battery.percentage")
zed_health = raw("zedstatus", "ZED stack health", f"{D}/zed_stack/status.data")
status_col = split(split("StateTransitions!status", battery, "column", 72), zed_health, "column", 42)

# --- Flight tab ----------------------------------------------------------------------------------------------------------------
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
    },
    "layers": grid(),
}
zed_left = image("zedleft", "ZED left (compressed)", f"{ZED}/left/color/rect/image/compressed")
chase = image("chase", "Chase cam (sim)", f"{D}/chase/image")
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
flight = split(split("3D!flight", split(zed_left, chase, "column", 55), "row", 62), split(alt, xy, "row", 50), "column", 64)

# --- Camera tab (the heavy topics) ---------------------------------------------------------------------------------------------
cam_left = image("camleft", "ZED left (raw)", f"{ZED}/left/color/rect/image")
depth = image("depth", "ZED depth [0.3-10 m, turbo; script depth_mm]", "/studio_script/depth_mm",
              colorMode="colormap", colorMap="turbo", minValue=300, maxValue=10000)
conf = image("confidence", "Depth confidence [blue good - red bad; script confidence_u16]", "/studio_script/confidence_u16",
             colorMode="colormap", colorMap="turbo", minValue=0, maxValue=10000)
flow = image("flow", "PMW3901 optical flow (arrow = motion over ground)", f"{D}/optical_flow/image")
cfg["3D!cloud"] = {   # default camera: a custom cameraState left the cloud out of view
    TITLE: "ZED point cloud", "followTf": "zed_camera_link", "followMode": "follow-pose",
    "scene": {"transforms": {"showLabel": False, "axisScale": 0.3}},
    "topics": {f"{ZED}/point_cloud/cloud_registered": {"visible": True, "pointSize": 2, "colorMode": "rgb", "colorField": "rgb", "decayTime": 0}},
    "layers": grid(),
}
camera = split(split(split(cam_left, depth, "row", 50), split(conf, flow, "row", 50), "column", 50), "3D!cloud", "row", 60)

# --- Debug tab -----------------------------------------------------------------------------------------------------------------
cfg["RosOut!log"] = {TITLE: "Log (/rosout)", "searchTerms": [], "minLogLevel": 2, "topicToRender": "/rosout"}
fcu_state = raw("fcustate", "mavros/state (full)", f"{D}/mavros/state")
imu = plot("imu", "FC IMU acceleration [m/s^2]", [
    (f"{D}/mavros/imu/data.linear_acceleration.x", "ax", "#f85149"),
    (f"{D}/mavros/imu/data.linear_acceleration.y", "ay", "#3fb950"),
    (f"{D}/mavros/imu/data.linear_acceleration.z", "az", "#58a6ff")], "m/s^2")
cfg["TopicGraph!graph"] = {TITLE: "Topic graph"}
debug = split("RosOut!log", split(split(fcu_state, imu, "column", 40), "TopicGraph!graph", "column", 60), "row", 45)

cfg["Tab!main"] = {"activeTabIdx": 0, "tabs": [
    {"title": "Flight", "layout": flight}, {"title": "Camera", "layout": camera}, {"title": "Debug", "layout": debug}]}

layout = {"configById": cfg, "globalVariables": {}, "userNodes": USER_SCRIPTS, "playbackConfig": {"speed": 1.0},
          "layout": split(status_col, "Tab!main", "row", 18)}
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "raptor.json")
with open(out, "w") as f:
    json.dump(layout, f, indent=2)
    f.write("\n")
print(f"{out}: {len(cfg)} panels, {len(USER_SCRIPTS)} user scripts")
