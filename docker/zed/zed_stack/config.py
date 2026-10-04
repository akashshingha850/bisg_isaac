"""docker/zed/zed.yaml -> zed_wrapper parameters + the list of services to start.

One file, one block per ZED SDK module. A block's keys are the wrapper's own parameter names; `enabled` is the module's
master switch. Everything is checked against the wrapper's shipped config (common_stereo.yaml, zedm.yaml,
object_detection.yaml), so a misspelt key or a wrong type fails here, not as a silent default inside the camera node.

Pure python + PyYAML: runs on the host, in the ZED/ROS containers and inside the Isaac Sim launcher.

    cfg = load("docker/zed/zed.yaml", sim=True)
    cfg.wrapper_params()      # {"general": {...}, "pos_tracking": {...}, ...}  (what `ros__parameters:` holds)
    cfg.services()            # {"px4_bridge": {...}, "qgc_video": {...}}
"""
import copy
import difflib
import os

import yaml

ZED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))          # docker/zed/
ROOT = os.path.abspath(os.path.join(ZED_DIR, "..", ".."))                          # repo root
DEFAULT_CONFIG = os.path.join(ZED_DIR, "zed.yaml")
WRAPPER_CONFIG_DIRS = (
    os.path.join(ZED_DIR, "zed-ros2-wrapper", "zed_wrapper", "config"),
    "/workspace/docker/zed/zed-ros2-wrapper/zed_wrapper/config",
    "/opt/ros/jazzy/share/zed_wrapper/config",
)
CAMERA_MODEL = "zedm"

# yaml block -> (wrapper section, the wrapper key `enabled` maps onto, SDK module it exposes)
MODULES = {
    "camera":              ("general",            None,                   "Camera"),
    "video":               ("video",              None,                   "Camera / video"),
    "sensors":             ("sensors",            None,                   "Sensors"),
    "depth":               ("depth",              None,                   "Depth sensing"),
    "region_of_interest":  ("region_of_interest", "automatic_roi",        "Region of interest"),
    "positional_tracking": ("pos_tracking",       "pos_tracking_enabled", "Positional tracking"),
    "global_localization": ("gnss_fusion",        "gnss_fusion_enabled",  "Global localization"),
    "spatial_mapping":     ("mapping",            "mapping_enabled",      "Spatial mapping"),
    "plane_detection":     ("mapping",            "publish_det_plane",    "Plane detection"),
    "object_detection":    ("object_detection",   "od_enabled",           "Object detection"),
    "body_tracking":       ("body_tracking",      "bt_enabled",           "Body tracking"),
    "streaming":           ("stream_server",      "stream_enabled",       "Streaming"),
    "recording":           ("svo",                None,                   "Recording (SVO)"),
}
# keys the `mapping` section shares between two blocks
PLANE_KEYS = {"pd_max_distance_threshold", "pd_normal_similarity_threshold", "clicked_point_topic", "publish_det_plane"}
# valid in the wrapper but absent from its default yaml (commented out there)
EXTRA_KEYS = {"region_of_interest": {"manual_polygon"}}
# modules that cannot run without depth
NEEDS_DEPTH = ("positional_tracking", "spatial_mapping", "plane_detection", "object_detection", "body_tracking")

ENUMS = {
    ("general", "grab_resolution"): {"HD2K", "HD1080", "HD720", "VGA", "AUTO"},
    ("depth", "depth_mode"): {"NEURAL_LIGHT", "NEURAL", "NEURAL_PLUS"},
    ("depth", "point_cloud_res"): {"COMPACT", "REDUCED"},
    ("pos_tracking", "pos_tracking_mode"): {"AUTO", "GEN_1", "GEN_3"},
    ("object_detection", "detection_model"): {"MULTI_CLASS_BOX_FAST", "MULTI_CLASS_BOX_MEDIUM", "MULTI_CLASS_BOX_ACCURATE",
                                              "PERSON_HEAD_BOX_FAST", "PERSON_HEAD_BOX_ACCURATE", "CUSTOM_YOLOLIKE_BOX_OBJECTS"},
    ("object_detection", "filtering_mode"): {"NONE", "NMS3D", "NMS3D_PER_CLASS"},
    ("body_tracking", "model"): {"HUMAN_BODY_FAST", "HUMAN_BODY_MEDIUM", "HUMAN_BODY_ACCURATE"},
    ("body_tracking", "body_format"): {"BODY_18", "BODY_34", "BODY_38"},
    ("stream_server", "codec"): {"H264", "H265"},
    ("svo", "svo_encoding_preset"): {"DEFAULT", "ULTRAFAST", "FAST", "MEDIUM", "SLOW"},
}

# service -> (defaults, {sub-module: defaults}); a key not here is rejected, like a wrapper key
SERVICES = {
    "px4_bridge": ({"enabled": False}, {
        "health": {"enabled": True, "depth_min_valid": 0.3, "timeout_s": 2.0},
        "odometry": {"enabled": False, "restamp": False, "min_rate_hz": 5.0},
        "obstacle_distance": {"enabled": False, "band": 0.6, "min_range": 0.3, "max_range": 8.0, "rate_hz": 10.0},
    }),
    "qgc_video": ({"enabled": False, "topic": "", "host": "127.0.0.1", "port": 5600, "bitrate": 2000, "fps": 0,
                   "encoder": "auto"}, {}),
}


class ConfigError(ValueError):
    pass


def deep_merge(a, b):
    out = copy.deepcopy(a)
    for k, v in (b or {}).items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


def _flatten_params(raw):
    return (raw.get("/**") or {}).get("ros__parameters") or {}


def _wrapper_dir():
    for d in WRAPPER_CONFIG_DIRS:
        if os.path.isfile(os.path.join(d, "common_stereo.yaml")):
            return d
    raise ConfigError("zed_wrapper config not found (docker/zed/zed-ros2-wrapper): run scripts/fetch_sources.sh")


def wrapper_schema():
    """{section: {key: default}} from the wrapper's own YAML files (the model file wins over the common one)."""
    d = _wrapper_dir()
    schema = {}
    for name in ("common_stereo.yaml", f"{CAMERA_MODEL}.yaml", "object_detection.yaml"):
        with open(os.path.join(d, name)) as f:
            schema = deep_merge(schema, _flatten_params(yaml.safe_load(f)))
    return schema


def _type_ok(default, value):
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, (int, float)):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if isinstance(default, str):
        return isinstance(value, str)
    return True


def _suggest(key, valid):
    near = difflib.get_close_matches(key, sorted(valid), n=1)
    return f" (did you mean '{near[0]}'?)" if near else ""


class StackConfig:
    def __init__(self, data, path="<memory>", sim=False):
        self.path = path
        self.sim = sim
        self.data = copy.deepcopy(data)
        if sim:
            overlay = self.data.get("sim") or {}
            self.data = deep_merge({k: v for k, v in self.data.items() if k != "sim"}, overlay)
        self.data.pop("sim", None)
        self._schema = None
        self._params = None

    # ---- module blocks -> wrapper parameters
    def module(self, name):
        return self.data.get(name) or {}

    def enabled(self, name):
        """Module master switch. Modules without `enabled` (camera, video, sensors, recording) are always on."""
        blk = self.module(name)
        if name == "depth":
            return blk.get("enabled", True) is not False
        return bool(blk.get("enabled", MODULES[name][1] is None))

    def wrapper_params(self):
        if self._params is None:
            self._params = self._compile()
        return copy.deepcopy(self._params)

    def _compile(self):
        schema = self._schema = wrapper_schema()
        unknown_blocks = set(self.data) - set(MODULES) - {"services"}
        if unknown_blocks:
            k = sorted(unknown_blocks)[0]
            raise ConfigError(f"{self.path}: unknown block '{k}'{_suggest(k, set(MODULES) | {'services', 'sim'})}")
        params = {}
        for name, (section, enable_key, _) in MODULES.items():
            blk = dict(self.module(name))
            if not isinstance(self.data.get(name) or {}, dict):
                raise ConfigError(f"{self.path}: block '{name}' must be a mapping")
            enabled = blk.pop("enabled", None)
            classes = blk.pop("classes", None) if name == "object_detection" else None
            valid = set(schema.get(section, {})) | EXTRA_KEYS.get(name, set())
            if section == "mapping":
                valid = (valid & PLANE_KEYS) if name == "plane_detection" else (valid - PLANE_KEYS)
            if enable_key:
                valid -= {enable_key}
            out = params.setdefault(section, {})
            for key, value in blk.items():
                if key not in valid:
                    raise ConfigError(f"{self.path}: {name}.{key} is not a zed_wrapper parameter{_suggest(key, valid)}")
                default = schema.get(section, {}).get(key)
                if default is not None and not _type_ok(default, value):
                    raise ConfigError(f"{self.path}: {name}.{key} = {value!r}: expected {type(default).__name__}")
                allowed = ENUMS.get((section, key))
                if allowed and value not in allowed:
                    raise ConfigError(f"{self.path}: {name}.{key} = {value!r}: one of {', '.join(sorted(allowed))}")
                out[key] = value
            if name == "depth" and enabled is False:
                out["depth_mode"] = "NONE"
            if enable_key and enabled is not None:
                out[enable_key] = bool(enabled)
            if classes is not None:
                valid_cls = set(schema["object_detection"]["class"])
                for cls, spec in classes.items():
                    if cls not in valid_cls:
                        raise ConfigError(f"{self.path}: object_detection.classes.{cls} unknown{_suggest(cls, valid_cls)}")
                    bad = set(spec) - {"enabled", "confidence_threshold"}
                    if bad:
                        raise ConfigError(f"{self.path}: object_detection.classes.{cls}.{sorted(bad)[0]} unknown")
                out["class"] = {c: dict(s) for c, s in classes.items()}
        if self.enabled("depth") is False:
            for name in NEEDS_DEPTH:
                if self.enabled(name):
                    raise ConfigError(f"{self.path}: {name} is on but depth is off (depth.enabled: false): every one of "
                                      f"{', '.join(NEEDS_DEPTH)} needs the depth map")
        if self.enabled("plane_detection") and not self.enabled("positional_tracking"):
            raise ConfigError(f"{self.path}: plane_detection needs positional_tracking")
        return {s: v for s, v in params.items() if v}

    def wrapper_yaml(self):
        """The text of the `ros_params_override_path` file."""
        return yaml.safe_dump({"/**": {"ros__parameters": self.wrapper_params()}}, sort_keys=False, default_flow_style=False)

    # ---- services
    def services(self):
        raw = self.data.get("services") or {}
        bad = set(raw) - set(SERVICES)
        if bad:
            k = sorted(bad)[0]
            raise ConfigError(f"{self.path}: unknown service '{k}'{_suggest(k, set(SERVICES))}")
        out = {}
        for name, (defaults, subs) in SERVICES.items():
            spec = raw.get(name) or {}
            valid = set(defaults) | set(subs)
            for key in spec:
                if key not in valid:
                    raise ConfigError(f"{self.path}: services.{name}.{key} unknown{_suggest(key, valid)}")
            merged = {k: spec.get(k, v) for k, v in defaults.items()}
            for sub, sub_defaults in subs.items():
                sspec = spec.get(sub) or {}
                for key in sspec:
                    if key not in sub_defaults:
                        raise ConfigError(f"{self.path}: services.{name}.{sub}.{key} unknown{_suggest(key, sub_defaults)}")
                merged[sub] = {k: sspec.get(k, v) for k, v in sub_defaults.items()}
            for key, default in defaults.items():
                if not _type_ok(default, merged[key]):
                    raise ConfigError(f"{self.path}: services.{name}.{key} = {merged[key]!r}: expected {type(default).__name__}")
            out[name] = merged
        return out

    def service_enabled(self, name):
        return bool(self.services()[name]["enabled"])

    def bridge_modules(self):
        """Enabled px4_bridge modules -> their settings (empty when the bridge itself is off)."""
        br = self.services()["px4_bridge"]
        if not br["enabled"]:
            return {}
        return {m: {k: v for k, v in br[m].items() if k != "enabled"} for m in SERVICES["px4_bridge"][1] if br[m]["enabled"]}

    def plan_services(self):
        """Names of compose services `./bisg zed up` must run next to the wrapper."""
        run = []
        if self.bridge_modules():
            run.append("zed-bridge")
        if self.service_enabled("qgc_video"):
            run.append("zed-video")
        return run


def load(path=None, sim=None):
    """sim=None: follow $ZED_STACK_SIM (1 = apply the `sim:` deltas) — the containers set it, so one call serves both worlds."""
    if sim is None:
        sim = os.environ.get("ZED_STACK_SIM") == "1"
    path = path or os.environ.get("ZED_STACK_CONFIG") or DEFAULT_CONFIG
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        raise ConfigError(f"{path}: not found")
    except yaml.YAMLError as e:
        raise ConfigError(f"{path}: invalid YAML: {e}")
    cfg = StackConfig(data, path, sim)
    cfg.wrapper_params()      # validate eagerly
    cfg.services()
    return cfg
