"""python3 -m zed_stack.bridge — the px4_bridge service (compose `zed-bridge`).

Env: DRONE_ID, ZED_STACK_CONFIG (default docker/zed/zed.yaml), ZED_STACK_SIM=1 (apply the sim: deltas, use /clock).
Which modules run, and their settings, come from services.px4_bridge in docker/zed/zed.yaml.
"""
import os
import signal
import sys

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter

from .. import config
from .common import Context
from .health import Health
from .obstacle import ObstacleDistance
from .odometry import Odometry2Px4

MODULES = {"odometry": Odometry2Px4, "obstacle_distance": ObstacleDistance}


def main():
    sim = os.environ.get("ZED_STACK_SIM", "0") == "1"
    cfg = config.load(sim=sim)
    wanted = cfg.bridge_modules()
    rclpy.init()
    node = Node("zed_px4_bridge", parameter_overrides=[Parameter("use_sim_time", value=sim)])
    ctx = Context(os.environ.get("DRONE_ID", "1"), sim)
    if not wanted:
        node.get_logger().warn("no px4_bridge module enabled in docker/zed/zed.yaml: nothing to do")
    for name, settings in wanted.items():
        if name != "health":
            ctx.modules[name] = MODULES[name](node, ctx, settings)
    if "health" in wanted:
        ctx.modules["health"] = Health(node, ctx, wanted["health"], cfg)
    node.get_logger().info(f"px4_bridge drone {ctx.drone_id}: {', '.join(wanted) or 'idle'} (sim={sim})")
    signal.signal(signal.SIGTERM, signal.default_int_handler)      # `compose stop` -> clean exit (we are PID 1)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
