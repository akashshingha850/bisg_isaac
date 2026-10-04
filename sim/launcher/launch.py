#!/usr/bin/env python3
"""
bisg_isaac Pegasus launcher — YAML-driven Isaac Sim standalone app.

    /isaac-sim/python.sh sim/launcher/launch.py --config docker/sim/configs/single_iris.yaml

Reads the scenario file, creates the SimulationApp (headless or not), loads the
world, spawns each vehicle with a PX4 MAVLink backend (PX4 SITL autolaunched by
Pegasus, instance = vehicle id), then steps the world until the app closes,
SIGTERM arrives, or app.exit_after_s elapses. Prints "[launch] sim ready" once
the first physics step has run so tests know when to start talking MAVLink.

Only stdlib + yaml is imported before SimulationApp is created (Isaac crashes if
any omni/isaacsim module is imported earlier).
"""
import argparse
import logging
import os
import signal
import sys
import time

import yaml


def parse_args():
    p = argparse.ArgumentParser(description="bisg_isaac Pegasus launcher")
    p.add_argument("--config", default=os.environ.get("SIM_CONFIG", "/workspace/docker/sim/configs/single_iris.yaml"))
    p.add_argument("--headless", action="store_true", help="force headless (also SIM_HEADLESS=1)")
    args, _ = p.parse_known_args()  # kit appends its own args
    return args


def load_scenario(path):
    """Read a scenario YAML. `extends: <file>` (relative to this file) loads that scenario
    first and deep-merges this one over it, so a variant only lists what it changes."""
    with open(path, "r") as f:
        cfg = yaml.safe_load(f) or {}
    base = cfg.pop("extends", None)
    if not base:
        return cfg

    def merge(a, b):
        out = dict(a)
        for k, v in b.items():
            out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
        return out
    return merge(load_scenario(os.path.join(os.path.dirname(path), base)), cfg)


ARGS = parse_args()
CFG = load_scenario(ARGS.config)

APP_CFG = CFG.get("app", {})
HEADLESS = bool(APP_CFG.get("headless", False)) or ARGS.headless or os.environ.get("SIM_HEADLESS", "0") == "1"
RENDER = bool(APP_CFG.get("render", True))
# Seeing a headless run (docs/remote-access.md). SIM_STREAM is what ./bisg derives from
# SIM_VIEW (config/bisg.conf or `./bisg up web|webrtc`); it wins over `app.stream:` here.
#   webrtc  interactive, Isaac Sim WebRTC Streaming Client, TCP 49100 + UDP 47998 (needs UDP: LAN/VPN)
#   web     still frames over one TCP port, so it survives a VS Code / SSH tunnel
#   both    run the two together
STREAM = str(os.environ.get("SIM_STREAM") or APP_CFG.get("stream") or "off").strip().lower()
STREAMING = STREAM in ("webrtc", "on", "true", "1", "yes", "both")
WEB_VIEW = STREAM in ("web", "browser", "both")
VIEW = STREAMING or WEB_VIEW
STREAM_ADDR = (os.environ.get("SIM_STREAM_ADDR") or APP_CFG.get("stream_addr") or "").strip()
WEB_PORT = int(os.environ.get("SIM_WEB_PORT") or APP_CFG.get("web_port") or 8899)
WEB_INTERVAL = float(os.environ.get("SIM_WEB_INTERVAL") or APP_CFG.get("web_interval") or 1.0)

# Configure only our named logger: touching the root logger would relabel Isaac's own
# DEBUG output (omni.*, pxr) with the [launch] prefix.
LOG = logging.getLogger("launch")
LOG.setLevel(getattr(logging, str(APP_CFG.get("log_level", "INFO")).upper(), logging.INFO))
_h = logging.StreamHandler(sys.stdout)
_h.setFormatter(logging.Formatter("[launch] %(levelname)s %(message)s"))
LOG.addHandler(_h)
LOG.propagate = False
LOG.info("config=%s headless=%s render=%s view=%s", ARGS.config, HEADLESS, RENDER, STREAM if VIEW else "off")
_T0 = time.time()


def phase(what):
    """Boot-phase timing: `[launch] INFO boot +NNs: <what>` (where the cold/warm boot time goes)."""
    LOG.info("boot +%.0fs: %s", time.time() - _T0, what)

# ---------------------------------------------------------------------------
# Isaac Sim must be created before any other omni / isaacsim / pegasus import.
# ---------------------------------------------------------------------------
from isaacsim import SimulationApp  # noqa: E402

# Performance knobs (docs/performance.md; NVIDIA "Sim Performance Optimization Handbook").
# Every key below is a real SimulationApp launcher option in Isaac 5.1/6.0; `extra_args` are
# passed straight to Kit as command-line settings.
PERF = CFG.get("perf", {}) or {}
_app_cfg = {"headless": HEADLESS}
if (CFG.get("app") or {}).get("viewport_hud", True):
    # Kit's own viewport HUD (the "Display > Heads Up Display" menu), on at start instead of by hand.
    # displayOptions bitmask: SimulationApp's default 3094 + FPS (1<<0), Device (1<<13), Host (1<<14) memory.
    _app_cfg["display_options"] = 3094 | (1 << 0) | (1 << 13) | (1 << 14)
for _k in ("disable_viewport_updates", "limit_cpu_threads", "sync_loads", "renderer",
           "active_gpu", "physics_gpu", "multi_gpu", "max_gpu_count", "width", "height",
           "anti_aliasing", "denoiser", "fast_shutdown"):
    if PERF.get(_k) is not None:
        _app_cfg[_k] = PERF[_k]
# Headless runs never need viewport updates; opt out explicitly unless the config says otherwise.
if HEADLESS and "disable_viewport_updates" not in _app_cfg:
    _app_cfg["disable_viewport_updates"] = True

if VIEW:
    # Both view modes send a rendered viewport over the network: the headless/perf shortcuts that
    # skip rendering would hand the client a frozen black image, so undo them here.
    if not RENDER:
        LOG.warning("view on: forcing render=true (app.render was false; nothing to show otherwise)")
        RENDER = True
    if _app_cfg.get("disable_viewport_updates"):
        LOG.warning("view on: re-enabling viewport updates (a viewed viewport must keep drawing)")
    _app_cfg["disable_viewport_updates"] = False
    _app_cfg.setdefault("hide_ui", False)                 # the client shows the normal Isaac UI
    _app_cfg.setdefault("renderer", "RaytracedLighting")
    _app_cfg.setdefault("width", 1280)                    # view resolution (VRAM: risk R1)
    _app_cfg.setdefault("height", 720)
    _app_cfg.setdefault("window_width", 1920)
    _app_cfg.setdefault("window_height", 1080)

_extra = list(PERF.get("extra_args") or [])
if PERF.get("skip_material_loading"):          # big load-time win, but untextured: physics-only tests
    _extra.append("--/app/renderer/skipMaterialLoading=true")
if PERF.get("min_frame_rate") is not None:     # PhysX catch-up clamp: higher = favour FPS over sim-time
    _extra.append(f"--/persistent/simulation/minFrameRate={int(PERF['min_frame_rate'])}")
if PERF.get("physx_threads") is not None:
    _extra.append(f"--/persistent/physics/numThreads={int(PERF['physx_threads'])}")
if STREAMING:
    # Isaac 6.0: omni.kit.livestream.app (the 5.1 omni.services.livestream.nvcf is gone). Its defaults live in
    # isaacsim.exp.full.streaming.kit, which the python kit we run does not load, so set them here.
    _extra += ["--/exts/omni.kit.livestream.app/primaryStream.signalPort=49100",
               "--/exts/omni.kit.livestream.app/primaryStream.streamPort=47998",
               "--/exts/omni.kit.livestream.app/primaryStream.streamType=webrtc"]
    if STREAM_ADDR:
        # Clients outside this machine need the address they should send media to (LAN/public IP).
        _extra.append(f"--/exts/omni.kit.livestream.app/primaryStream.publicIp={STREAM_ADDR}")
# ZED SDK mode (docs/zed-sdk-sim.md): the zed-isaac-sim extension must be on Kit's path before Kit starts.
from zed_sdk_cfg import EXT_ID as ZED_EXT_ID, ext_folder as zed_ext_folder, zed_source  # noqa: E402 (stdlib only)
ZED_SDK_RIG = any(((v.get("sensors") or {}).get("zed") or {}).get("enabled", False)
                  and zed_source((v.get("sensors") or {}).get("zed") or {}) == "sdk" for v in CFG.get("vehicles", []))
if ZED_SDK_RIG:
    _extra += ["--ext-folder", zed_ext_folder(), "--enable", ZED_EXT_ID]
    LOG.info("ZED SDK mode: extension %s from %s", ZED_EXT_ID, zed_ext_folder())
if _extra:
    _app_cfg["extra_args"] = _extra
LOG.info("SimulationApp config: %s", _app_cfg)

simulation_app = SimulationApp(_app_cfg)
phase("SimulationApp up")

if STREAMING:
    # Same sequence as NVIDIA's own standalone example
    # (/isaac-sim/standalone_examples/api/isaacsim.simulation_app/livestream.py).
    from isaacsim.core.experimental.utils.app import enable_extension  # noqa: E402

    simulation_app.set_setting("/app/window/drawMouse", True)
    if not enable_extension("omni.kit.livestream.app"):
        raise SystemExit("[launch] could not enable omni.kit.livestream.app — WebRTC stream unavailable")
    _where = STREAM_ADDR or "127.0.0.1"
    print(f"[launch] livestream webrtc ready — connect the Isaac Sim WebRTC Streaming Client to {_where} "
          f"(TCP 49100 signalling, UDP 47998 media)", flush=True)

import carb  # noqa: E402
import omni.timeline  # noqa: E402
import omni.usd  # noqa: E402
# Isaac Sim 6.0 removed omni.isaac.core.World (archive/docs/migrate.md §14): physics/render settings, the physics
# clock and per-step callbacks now come from SimulationManager / RenderingManager.
from isaacsim.core.rendering_manager import RenderingManager  # noqa: E402
from isaacsim.core.simulation_manager import SimulationEvent, SimulationManager  # noqa: E402
from scipy.spatial.transform import Rotation  # noqa: E402

from pegasus.simulator.params import ROBOTS, SIMULATION_ENVIRONMENTS  # noqa: E402
from pegasus.simulator.logic.backends.px4_mavlink_backend import PX4MavlinkBackend, PX4MavlinkBackendConfig  # noqa: E402
from pegasus.simulator.logic.vehicles.multirotor import Multirotor, MultirotorConfig  # noqa: E402
if PERF.get("pegasus_fast", True):   # per-step speed-ups for Pegasus on 6.0 (sim/launcher/pegasus_fast.py)
    import pegasus_fast  # noqa: E402
    pegasus_fast.apply()
from pegasus.simulator.logic.interface.pegasus_interface import PegasusInterface  # noqa: E402
phase("pegasus imported")


class WebView:
    """Serve the viewport as a still image over one TCP port.

    The WebRTC client needs UDP 47998, which a VS Code / SSH port forward cannot carry.
    This is the fallback that survives such a tunnel: forward SIM_WEB_PORT and open the page
    in a browser (docs/remote-access.md). Frames are captured from the main thread in the
    physics loop; the HTTP thread only hands out the last finished PNG.
    """

    def __init__(self, port, interval, directory="/tmp/bisg-view"):
        self.port = int(port)
        self.interval = max(float(interval), 0.1)
        self.dir = directory
        self.paths = [os.path.join(directory, "a.png"), os.path.join(directory, "b.png")]
        self.idx = 0
        self.ready = None        # last capture known to be complete
        self.pending = None      # capture in flight
        self.t_last = 0.0
        self.enabled = True
        os.makedirs(directory, exist_ok=True)

    def _page(self):
        return f"""<!doctype html><html><head><meta charset="utf-8">
<title>bisg sim view</title><style>
 body{{margin:0;background:#111;color:#ddd;font:14px system-ui,sans-serif;display:flex;
      flex-direction:column;height:100vh}}
 header{{padding:6px 10px;background:#1b1b1b;border-bottom:1px solid #333}}
 img{{flex:1;min-height:0;object-fit:contain;width:100%}}
 #msg{{padding:10px}} code{{color:#8ab4f8}}
</style></head><body>
<header>bisg sim — still view, refresh {self.interval:g}s.
 Interactive view: WebRTC client (see <code>./bisg stream</code>).</header>
<div id="msg">waiting for the first frame (the sim renders it once the world is loaded)…</div>
<img id="v" alt="" style="display:none">
<script>
 const img=document.getElementById('v'), msg=document.getElementById('msg');
 function tick(){{
   const n=new Image();
   n.onload=()=>{{img.src=n.src;img.style.display='';msg.style.display='none';}};
   n.src='/frame.png?t='+Date.now();
 }}
 tick(); setInterval(tick, {int(self.interval * 1000)});
</script></body></html>""".encode()

    def start(self):
        import http.server  # noqa: WPS433
        import socketserver  # noqa: WPS433
        import threading  # noqa: WPS433

        view = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def _send(self, code, body, ctype):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):  # noqa: N802
                if self.path.startswith("/frame.png"):
                    try:
                        with open(view.ready, "rb") as fh:
                            self._send(200, fh.read(), "image/png")
                    except (TypeError, OSError):
                        self._send(503, b"no frame yet", "text/plain")
                elif self.path in ("/", "/index.html"):
                    self._send(200, view._page(), "text/html; charset=utf-8")
                else:
                    self._send(404, b"not found", "text/plain")

            def log_message(self, *_args):  # keep Kit's stdout readable
                pass

        class Server(socketserver.ThreadingTCPServer):
            daemon_threads = True
            allow_reuse_address = True

        try:
            self.server = Server(("0.0.0.0", self.port), Handler)
        except OSError as exc:
            LOG.warning("web view disabled: cannot bind port %d (%s)", self.port, exc)
            self.enabled = False
            return
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        print(f"[launch] web view ready — http://{STREAM_ADDR or '127.0.0.1'}:{self.port}/ "
              f"(still frames every {self.interval:g}s; forward TCP {self.port} to reach it remotely)",
              flush=True)

    def maybe_capture(self):
        """Issue one viewport capture if the interval has elapsed. Never raises."""
        if not self.enabled:
            return
        now = time.time()
        if now - self.t_last < self.interval:
            return
        self.t_last = now
        # Publish first: the capture issued last time has had a full interval to land, and a
        # failure below should still leave the previous frame on offer.
        if self.pending and os.path.exists(self.pending):
            self.ready, self.pending = self.pending, None
        try:
            from omni.kit.viewport.utility import capture_viewport_to_file, get_active_viewport  # noqa: WPS433

            viewport = get_active_viewport()
            if viewport is None:
                return
            target = self.paths[self.idx]
            self.idx ^= 1
            capture_viewport_to_file(viewport, target)
            self.pending = target
        except Exception as exc:  # noqa: BLE001 — a broken view must never stop the sim
            LOG.warning("web view: capture failed, disabling (%s)", exc)
            self.enabled = False


def resolve_world(world_cfg):
    usd = world_cfg.get("usd_path")
    if usd:
        return usd
    preset = world_cfg.get("preset", "Curved Gridroom")
    if preset not in SIMULATION_ENVIRONMENTS:
        raise SystemExit(f"[launch] unknown world preset {preset!r}; options: {list(SIMULATION_ENVIRONMENTS)}")
    return SIMULATION_ENVIRONMENTS[preset]


def resolve_vehicle_usd(v_cfg):
    usd = v_cfg.get("usd_path")
    if usd:
        return usd
    model = v_cfg.get("model", "Iris")
    if model not in ROBOTS:
        raise SystemExit(f"[launch] unknown vehicle model {model!r}; options: {list(ROBOTS)}")
    return ROBOTS[model]


def spawn_objects(objects):
    """Static test objects from the scenario (`world.objects`), e.g. a box to check ZED depth against.

    Each entry: {name, type: cuboid, position: [x,y,z] (centre, world ENU m), size: [sx,sy,sz] m,
    color: [r,g,b] 0-1}. Fixed (static colliders), so they show up in depth, cameras and physics.
    """
    import numpy as np  # noqa: WPS433
    from isaacsim.core.experimental.objects import Cube  # noqa: WPS433
    from pxr import UsdPhysics  # noqa: WPS433

    for i, o in enumerate(objects or []):
        kind = str(o.get("type", "cuboid"))
        if kind != "cuboid":
            raise SystemExit(f"[launch] world.objects[{i}]: unsupported type {kind!r} (cuboid only)")
        name = str(o.get("name", f"object_{i}"))
        pos = np.array([float(x) for x in o.get("position", [0.0, 0.0, 0.5])])
        size = np.array([float(x) for x in o.get("size", [1.0, 1.0, 1.0])])
        color = np.array([float(x) for x in o.get("color", [0.5, 0.5, 0.5])])
        path = f"/World/test_objects/{name}"
        Cube(path, sizes=1.0, colors=color.reshape(1, 3), positions=pos.reshape(1, 3), scales=size.reshape(1, 3))
        # No RigidBodyAPI = static collider (what 5.1's FixedCuboid was).
        UsdPhysics.CollisionAPI.Apply(omni.usd.get_context().get_stage().GetPrimAtPath(path))
        LOG.info("object %s: cuboid %s m at %s (faces x %.2f..%.2f, y %.2f..%.2f, z %.2f..%.2f)", name,
                 size.tolist(), pos.tolist(), *(v for a in range(3) for v in (pos[a] - size[a] / 2, pos[a] + size[a] / 2)))


def apply_px4_params(params_file):
    """Hand a config/px4/*.params file to PX4 SITL at boot.

    PX4's posix rcS runs `param set <name> <value>` for every PX4_PARAM_<name> env var before
    any module starts, and Pegasus launches PX4 with this process's environment. So the
    reboot_required EKF2 params (EKF2_HGT_REF, EKF2_MAG_TYPE) take effect on the first boot:
    there is no push + reboot step, which SITL can't do anyway (Pegasus runs PX4 from a fresh
    temp dir each launch, so a saved param never survives). Applies to every PX4 instance.
    """
    if not params_file:
        return
    path = params_file if os.path.isabs(params_file) else os.path.join("/workspace", params_file)
    with open(path) as f:
        for line in f:
            line = line.split("#", 1)[0].split()
            if line:  # "NAME VALUE MAV_PARAM_TYPE" (scripts/push_px4_params.py format)
                os.environ[f"PX4_PARAM_{line[0]}"] = line[1]
                LOG.info("px4 param %s = %s (%s)", line[0], line[1], params_file)


class SimClock:
    """Publish /clock (sim time) once per physics step (docs/interface-contract.md).

    PX4 SITL runs on sim time: Pegasus stamps every HIL_SENSOR with its accumulated physics time
    and PX4 sets its own clock from it. Everything ROS-side must run on the same clock
    (use_sim_time), or MAVLink timesync sees two clocks drifting apart at (1 - rtf) s/s, never
    converges, and PX4 stamps external-vision samples on arrival or with a stale offset.
    This is driven by the physics callback, not an OmniGraph tick: action graphs only
    evaluate on rendered frames (1 in `render_every` steps).
    """

    def __init__(self):
        from isaacsim.core.experimental.utils.app import enable_extension  # noqa: WPS433
        enable_extension("isaacsim.ros2.bridge")  # puts Isaac's bundled Jazzy rclpy on sys.path
        import rclpy  # noqa: WPS433
        from rclpy.qos import QoSProfile, ReliabilityPolicy  # noqa: WPS433
        from rosgraph_msgs.msg import Clock  # noqa: WPS433

        try:
            rclpy.init()
        except RuntimeError:  # already initialised (Pegasus ROS2Backend does the same)
            pass
        self.msg = Clock()
        self.node = rclpy.create_node("bisg_sim_clock")
        # Reliable keep-last-1: compatible with best-effort time-source readers and with ros2 CLI tools.
        self.pub = self.node.create_publisher(Clock, "/clock", QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE))
        self._cb = SimulationManager.register_callback(self.on_step, SimulationEvent.PHYSICS_POST_STEP)
        LOG.info("sim clock: publishing /clock every physics step (use_sim_time:=true on the ROS side)")

    def on_step(self, _step_size, _context=None):
        # Same base as IsaacReadSimulationTime, which stamps the ZED images/IMU/TF.
        self.msg.clock.sec, self.msg.clock.nanosec = divmod(int(round(SimulationManager.get_simulation_time() * 1e9)), 1_000_000_000)
        self.pub.publish(self.msg)


class App:
    def __init__(self, cfg):
        self.cfg = cfg
        self.timeline = omni.timeline.get_timeline_interface()
        self.pg = PegasusInterface()
        # World settings are applied by initialize_world() (physics dt) and RenderingManager.set_dt (loop dt).
        # physics_dt drives the PX4 sensor/mavlink rate (Pegasus default 1/250 s) — changing it
        # changes flight behaviour, so it stays null unless a scenario opts in.
        world = cfg.get("world", {})
        if any(world.get(k) is not None for k in ("physics_dt", "rendering_dt", "physics_device")):
            self.pg.set_world_settings(physics_dt=world.get("physics_dt"),
                                       rendering_dt=world.get("rendering_dt"),
                                       device=world.get("physics_device"))
            LOG.info("world settings: %s", self.pg._world_settings)
        self.pg.initialize_world()
        RenderingManager.set_dt(float(self.pg._world_settings.get("rendering_dt", 1.0 / 60.0)))
        self.vehicles = []
        self.previews = []  # drone-view windows (ZED left|depth + third eye) + depth products (drone_views.py, zed_depth.py)
        self.stop = False
        self.web = WebView(WEB_PORT, WEB_INTERVAL) if WEB_VIEW else None

        world_cfg = cfg.get("world", {})
        world_usd = resolve_world(world_cfg)
        LOG.info("loading world %s", world_usd)
        self.pg.load_asset(world_usd, "/World/layout")   # synchronous (load_environment defers to the first update)
        phase("world asset referenced")
        if world_cfg.get("add_ground_plane", False):
            from isaacsim.core.experimental.objects import GroundPlane  # noqa: WPS433
            GroundPlane("/World/bisg_ground", sizes=500.0, positions=[[0.0, 0.0, float(world_cfg.get("ground_z", 0.0))]])
            # 5.1 hid this plane (visible=False): it is only a collider under meshes that have none.
            from pxr import UsdGeom  # noqa: WPS433
            UsdGeom.Imageable(omni.usd.get_context().get_stage().GetPrimAtPath("/World/bisg_ground")).MakeInvisible()

        spawn_objects(world_cfg.get("objects"))

        px4_cfg = cfg.get("px4", {})
        apply_px4_params(px4_cfg.get("params_file"))
        for v in cfg.get("vehicles", []):
            self.spawn_vehicle(v, px4_cfg)

        phase("vehicles spawned")
        self.clock = SimClock() if cfg.get("app", {}).get("ros_clock", True) else None
        app_cfg = cfg.get("app", {})
        eye, target = app_cfg.get("viewport_eye"), app_cfg.get("viewport_target")
        follow_cfg = app_cfg.get("follow_cam") or {}
        self.follow = None
        if follow_cfg.get("enabled", False) and (not HEADLESS or STREAMING) and self.vehicles:
            try:   # Gazebo-style follow camera (sim/launcher/follow_cam.py); replaces the fixed start view
                from follow_cam import FollowCam  # noqa: WPS433
                self.follow = FollowCam(self.vehicles, follow_cfg)
                eye = target = None
            except Exception as exc:  # noqa: BLE001
                LOG.warning("could not start the follow camera: %s", exc)
        if self.follow is None and not (eye and target):
            # Kit's default perspective camera sits ~hundreds of metres away (blank view until you zoom in):
            # frame the spawned vehicles instead. Set viewport_eye + viewport_target to pin a view.
            import numpy as np  # noqa: WPS433
            pts = np.array([[float(x) for x in v.get("position", [0.0, 0.0, 0.07])]
                            for v in cfg.get("vehicles", [])] or [[0.0, 0.0, 0.07]])
            centre = pts.mean(axis=0)
            spread = float(np.linalg.norm(pts - centre, axis=1).max())
            eye = centre + np.array([-2.5 - spread, -2.0 - spread, 1.8 + 0.5 * spread])
            target = centre + np.array([0.0, 0.0, 0.5])
        if (not HEADLESS or STREAMING) and app_cfg.get("viewport_hud", True):
            try:   # real-time factor next to Kit's FPS line (sim/launcher/rtf_hud.py)
                import rtf_hud  # noqa: WPS433
                rtf_hud.install(SimulationManager.get_simulation_time)
            except Exception as exc:  # noqa: BLE001 — the HUD must never stop the sim
                LOG.warning("could not add the RTF line to the viewport HUD: %s", exc)
        if self.follow is None and (not HEADLESS or STREAMING):
            from isaacsim.core.rendering_manager import ViewportManager  # noqa: WPS433
            ViewportManager.set_camera_view("/OmniverseKit_Persp", eye=[float(x) for x in eye], target=[float(x) for x in target])
            LOG.info("viewport camera: eye %s -> target %s", [round(float(x), 2) for x in eye], [round(float(x), 2) for x in target])

    def spawn_vehicle(self, v, px4_cfg):
        vid = int(v.get("id", 0))
        mcfg = MultirotorConfig()
        backends = []

        mav = PX4MavlinkBackendConfig({
            "vehicle_id": vid,
            "px4_autolaunch": bool(px4_cfg.get("autolaunch", True)),
            "px4_dir": px4_cfg.get("px4_dir") or self.pg.px4_path,
            "px4_vehicle_model": px4_cfg.get("airframe") or self.pg.px4_default_airframe,
            "enable_lockstep": bool(px4_cfg.get("enable_lockstep", False)),
        })
        backends.append(PX4MavlinkBackend(mav))
        LOG.info("vehicle %d: PX4 SITL instance %d on tcp 4560+%d, MAV_SYS_ID %d, airframe %s",
                 vid, vid, vid, vid + 1, mav.px4_vehicle_model)

        ros2 = v.get("ros2", {})
        if ros2.get("enabled", False):
            from pegasus.simulator.logic.backends.ros2_backend import ROS2Backend  # noqa: WPS433
            backends.append(ROS2Backend(vehicle_id=vid + 1, config={
                "namespace": "drone_",           # Pegasus appends the id -> /drone_<id+1>/...
                "pub_state": ros2.get("pub_state", True),
                "pub_sensors": ros2.get("pub_sensors", False),
                "pub_graphical_sensors": ros2.get("pub_graphical_sensors", True),
                "sub_control": False,
            }))
            LOG.info("vehicle %d: ROS2 backend on namespace /drone_%d", vid, vid + 1)
        mcfg.backends = backends

        pos = [float(x) for x in v.get("position", [0.0, 0.0, 0.07])]
        quat = Rotation.from_euler("XYZ", [0.0, 0.0, float(v.get("yaw_deg", 0.0))], degrees=True).as_quat()
        prim = f"/World/drone_{vid + 1}"
        veh = Multirotor(prim, resolve_vehicle_usd(v), vid, pos, quat, config=mcfg)
        self.vehicles.append(veh)
        LOG.info("vehicle %d spawned at %s as %s", vid, pos, prim)

        third_eye_cfg = (self.cfg.get("app", {}).get("third_eye") or {})
        third_eye = None
        if third_eye_cfg.get("enabled", False) and (not HEADLESS or STREAMING):
            from third_eye import attach_third_eye  # noqa: WPS433
            third_eye = attach_third_eye(veh, third_eye_cfg)

        zed = v.get("sensors", {}).get("zed", {})
        if zed.get("enabled", False) and zed_source(zed) == "sdk":
            from zed_sdk_rig import attach_zed_sdk  # noqa: WPS433
            from zed_rig import publish_imu  # noqa: WPS433
            from zed_features import load_features  # noqa: WPS433
            attach_zed_sdk(veh, vid, f"/drone_{vid + 1}", zed, pos, Rotation.from_quat(quat))
            # The streamed ZED has no usable sensor channel (docs/zed-sdk-sim.md): the sim publishes the contract's
            # imu/data itself, from a physics IMU on the vehicle body, unless the params file switches it off.
            if load_features(zed).on("sensors.publish_imu", True):
                mount = [float(x) for x in zed.get("mount_xyz_rpy", [0.18, 0.0, -0.02, 0, 0, 0])][:3]
                publish_imu(f"{veh.prim_path}/body", f"/drone_{vid + 1}", mount, float(zed.get("imu_rate", 200.0)))
            LOG.info("vehicle %d: ZED SDK twin attached; start the wrapper with ./bisg zed up", vid)
        elif zed.get("enabled", False):
            from zed_rig import attach_zed_mini  # noqa: WPS433
            from zed_features import load_features  # noqa: WPS433
            features = load_features(zed)  # zed_wrapper switches: docker/zed/zed.yaml + overrides
            cams = attach_zed_mini(veh, f"/drone_{vid + 1}", zed, features)
            LOG.info("vehicle %d: ZED Mini rig attached on /drone_%d/zed/zed_node/...", vid, vid + 1)
            # A UI exists with a window (not headless) or a WebRTC stream (which shows the full UI).
            has_ui = not HEADLESS or STREAMING
            if zed.get("preview", False) and has_ui:
                from drone_views import DroneViews  # noqa: WPS433
                self.previews.append(DroneViews(cams, f"/drone_{vid + 1}", zed, third_eye,
                                                third_eye_cfg.get("preview_hz", 8.0)))
            view = zed.get("view", {}) or {}
            if (features.on("depth.publish_point_cloud") or features.on("depth.publish_disparity")
                    or features.on("mapping.mapping_enabled") or (has_ui and (view.get("point_cloud", False) or view.get("accumulate", view.get("fused_cloud", True))
                                    or view.get("fov_grid", True)))):
                from zed_depth import ZedDepthProducts  # noqa: WPS433
                self.previews.append(ZedDepthProducts(cams, f"/drone_{vid + 1}", zed, features,
                                                      sim_time=SimulationManager.get_simulation_time, has_ui=has_ui))

    def run(self):
        app_cfg = self.cfg.get("app", {})
        hb = int(app_cfg.get("heartbeat_steps", 0))
        exit_after = float(app_cfg.get("exit_after_s", 0) or 0)
        t0 = time.time()
        step = 0

        physics_dt = float(self.pg._world_settings.get("physics_dt", 1.0 / 250.0))
        # Cadence (Isaac 6.0): one simulation_app.update() per RenderingManager dt (= world.rendering_dt),
        # and Kit runs the physics sub-steps that fit in it (physics_dt each) — the render-per-N-steps
        # logic the 5.1 launcher needed for World.step(render=True) is built in now.
        # `step` below counts PHYSICS steps (SimulationManager), so heartbeat/perf lines keep their meaning.
        if not RENDER:
            LOG.warning("app.render=false: Isaac 6.0 has no World.step(render=False); the loop still calls "
                        "simulation_app.update() (viewport updates are disabled when headless, so rendering is mostly skipped)")
        LOG.info("loop cadence: 1 update per %.4fs (rendering_dt), physics_dt=%.4fs", RenderingManager.get_dt(), physics_dt)
        if self.web:
            self.web.start()
        self.timeline.play()
        phase("timeline.play, first update")
        simulation_app.update()
        phase("sim ready")
        print("[launch] sim ready", flush=True)
        t_hb = time.time()
        step_hb = SimulationManager.get_num_physics_steps()

        # `app.profile_s: N` — cProfile the loop for N wall seconds and log the top cumulative-time entries
        # (Python callbacks run from C++ show up too: Pegasus update_state, backends, graphs). docs/performance.md.
        prof_s = float(app_cfg.get("profile_s", 0) or 0)
        prof = None
        if prof_s:
            import cProfile  # noqa: WPS433
            prof = cProfile.Profile()
            prof.enable()
            t_prof = time.time()

        while simulation_app.is_running() and not self.stop:
            simulation_app.update()
            step = SimulationManager.get_num_physics_steps()
            if prof is not None and time.time() - t_prof > prof_s:
                import io, pstats  # noqa: WPS433,E401
                prof.disable()
                out = io.StringIO()
                st = pstats.Stats(prof, stream=out).sort_stats("cumulative")
                st.print_stats(45)
                LOG.info("profile (%.0f s, cumulative):\n%s", prof_s, out.getvalue())
                out = io.StringIO()
                pstats.Stats(prof, stream=out).sort_stats("tottime").print_stats(30)
                LOG.info("profile (%.0f s, own time):\n%s", prof_s, out.getvalue())
                prof = None
            if self.web:
                self.web.maybe_capture()
            if self.follow:
                self.follow.update()
            for p in self.previews:
                p.maybe_update()
            if hb and step - step_hb >= hb:
                # Real-time factor: >= 1.0 means the sim keeps up with wall clock.
                # `./bisg debug perf` reads these lines; see docs/performance.md.
                now = time.time()
                sps = (step - step_hb) / max(now - t_hb, 1e-6)
                t_hb, step_hb = now, step
                LOG.info("perf step %d %.0f steps/s rtf=%.2f", step, sps, sps * physics_dt)
                for i, veh in enumerate(self.vehicles):
                    try:
                        p = veh.state.position
                        LOG.info("step %d vehicle %d pos=[%.2f %.2f %.2f]", step, i, p[0], p[1], p[2])
                    except Exception:  # noqa: BLE001
                        pass
            if exit_after and (time.time() - t0) > exit_after:
                LOG.info("exit_after_s reached")
                break

        self.shutdown()

    def shutdown(self):
        if getattr(self, "_shut", False):
            return
        self._shut = True
        LOG.info("shutting down: stopping timeline, killing PX4, closing app")
        if getattr(self, "web", None) is not None and getattr(self.web, "server", None) is not None:
            try:
                self.web.server.shutdown()
            except Exception:  # noqa: BLE001
                pass
        try:
            self.timeline.stop()
        except Exception:  # noqa: BLE001
            pass
        # Pegasus kills PX4 in the backend destructors; be explicit so no SITL survives.
        for veh in self.vehicles:
            for b in getattr(veh, "_backends", []) or []:
                tool = getattr(b, "px4_tool", None)
                if tool is not None:
                    try:
                        tool.kill_px4()
                    except Exception:  # noqa: BLE001
                        pass
        try:
            simulation_app.close()
        except Exception:  # noqa: BLE001
            pass
        LOG.info("bye")


def main():
    app = App(CFG)

    def _sig(signum, _frame):
        print(f"[launch] signal {signum} received, stopping", flush=True)
        app.stop = True

    # Kit may install its own handlers during startup; ours are registered after
    # SimulationApp exists so they win. SIGTERM is what `docker compose stop` sends.
    signal.signal(signal.SIGTERM, _sig)
    signal.signal(signal.SIGINT, _sig)
    try:
        app.run()
    finally:
        app.shutdown()


if __name__ == "__main__":
    main()
