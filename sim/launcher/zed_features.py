"""
ZED SDK feature switches for the emulated sim rig: the same docker/zed/zed.yaml the real zed_wrapper is configured from
(compiled by zed_stack.config into the wrapper's own parameter names), plus optional per-scenario overrides.

    features = load_features(zed_cfg)          # zed_cfg = scenario `sensors.zed`
    on("depth.publish_point_cloud")

Scenario keys (sensors.zed):
    features:                                        # optional overrides, wrapper parameter names
      mapping: {mapping_enabled: true}

A switch that is on but not emulated here is logged once ("not simulated") so a sim run never
silently pretends to have a feature. archive/docs/zed-features.md lists what each switch does in sim/hw.
"""
import logging
import os
import sys

LOG = logging.getLogger("launch")

DEFAULT_FILE = "docker/zed/zed.yaml"

# Switches the sim implements (zed_rig.py / zed_depth.py / vio_mock). Everything else that is a
# feature switch (publish_* or *_enabled) is hardware-only.
SIMULATED = {
    "video.publish_left_right", "sensors.publish_imu", "sensors.publish_imu_tf",
    "depth.publish_depth_map", "depth.publish_point_cloud", "depth.publish_disparity",
    "pos_tracking.pos_tracking_enabled", "pos_tracking.publish_odom_pose", "pos_tracking.publish_tf",
    "mapping.mapping_enabled",
}
# Harmless when on in sim (frame/TF bookkeeping handled elsewhere, see vio_mock / interface-contract)
IGNORED = {"pos_tracking.publish_map_tf"}


def _merge(a, b):
    out = dict(a)
    for k, v in (b or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_features(zed_cfg: dict, workspace: str = "/workspace") -> "Features":
    zed_dir = os.path.join(workspace, "docker", "zed")      # zed_stack lives with the ZED image
    if zed_dir not in sys.path:
        sys.path.insert(0, zed_dir)
    from zed_stack import config  # noqa: E402  (the repo is bind-mounted at /workspace)
    path = zed_cfg.get("features_file", DEFAULT_FILE)
    path = path if os.path.isabs(path) else os.path.join(workspace, path)
    params = config.load(path, sim=True).wrapper_params()
    feats = Features(_merge(params, zed_cfg.get("features")), path)
    feats.report()
    return feats


class Features:
    def __init__(self, params: dict, source: str):
        self.p = params
        self.source = source

    def get(self, key: str, default=None):
        node = self.p
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def on(self, key: str, default: bool = False) -> bool:
        return bool(self.get(key, default))

    def report(self):
        simulated, missing = [], []
        for section, vals in self.p.items():
            if not isinstance(vals, dict):
                continue
            for k, v in vals.items():
                if not (k.startswith("publish_") or k.endswith("_enabled")) or v is not True:
                    continue
                key = f"{section}.{k}"
                if key in IGNORED:
                    continue
                (simulated if key in SIMULATED else missing).append(key)
        LOG.info("zed features (%s): simulated on: %s", self.source, ", ".join(sorted(simulated)) or "none")
        if missing:
            LOG.warning("zed features switched on but NOT simulated (real ZED SDK only): %s", ", ".join(sorted(missing)))
