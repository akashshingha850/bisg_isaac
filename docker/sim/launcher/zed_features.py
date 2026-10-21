"""
Read the ZED switches from docker/zed/zed.yaml, the file the real zed_wrapper is configured from (compiled by
zed_stack.config into the wrapper's own parameter names). The ZED SDK does the work; the sim only needs the few
switches that decide what the sim itself publishes (e.g. `sensors.publish_imu`).

    load_features(zed_cfg).on("sensors.publish_imu", True)
"""
import os
import sys

DEFAULT_FILE = "docker/zed/zed.yaml"


def load_features(zed_cfg: dict, workspace: str = "/workspace") -> "Features":
    zed_dir = os.path.join(workspace, "docker", "zed")      # zed_stack lives with the ZED image
    if zed_dir not in sys.path:
        sys.path.insert(0, zed_dir)
    from zed_stack import config  # noqa: E402  (the repo is bind-mounted at /workspace)
    path = zed_cfg.get("features_file", DEFAULT_FILE)
    path = path if os.path.isabs(path) else os.path.join(workspace, path)
    return Features(config.load(path, sim=True).wrapper_params())


class Features:
    def __init__(self, params: dict):
        self.p = params

    def on(self, key: str, default: bool = False) -> bool:
        node = self.p
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return bool(node)
