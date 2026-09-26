#!/usr/bin/env python3
"""Switch every MAVROS plugin node to use_sim_time:=true (sim stack only, docker/ros/entrypoint.sh).

MAVROS 2.15.1 creates each plugin as its own node with use_global_arguments(false)
(mavros/src/lib/plugin.cpp), so neither `-p use_sim_time:=true` nor a `--params-file` reaches
them — only mavros_node and the router get it. The `time` plugin answers PX4's MAVLink
TIMESYNC with its own node clock, and PX4 SITL runs on sim time: on the wall clock the offset
drifts at (1 - rtf) s/s, PX4 timesync never converges and external-vision samples get the
wrong timestamp. use_sim_time can be changed at runtime, so set it on every node under
/<ns>/mavros once they exist.

    mavros_sim_time.py /drone_1
"""
import sys
import time

import rclpy
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from rcl_interfaces.srv import SetParameters


def main():
    ns = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else ""
    prefix = f"{ns}/mavros"
    rclpy.init()
    node = rclpy.create_node("mavros_sim_time", namespace=ns or "/")
    param = Parameter(name="use_sim_time",
                      value=ParameterValue(type=ParameterType.PARAMETER_BOOL, bool_value=True))

    def targets():
        found = set()
        for name, nspace in node.get_node_names_and_namespaces():
            full = f"{nspace.rstrip('/')}/{name}"
            if full == prefix or full.startswith(prefix + "/"):
                found.add(full)
        return found

    # Plugins are created right after the FCU link opens; wait for the timesync one, then settle.
    deadline = time.time() + 120
    while f"{prefix}/time" not in targets():
        if time.time() > deadline:
            print(f"[mavros_sim_time] {prefix}/time never appeared — use_sim_time NOT set", flush=True)
            return 1
        rclpy.spin_once(node, timeout_sec=0.5)
    time.sleep(2.0)

    done, failed = set(), set()
    for _ in range(3):  # a second pass catches plugin nodes that were still starting
        for full in sorted(targets() - done):
            cli = node.create_client(SetParameters, f"{full}/set_parameters")
            if not cli.wait_for_service(timeout_sec=5.0):
                failed.add(full)
                continue
            fut = cli.call_async(SetParameters.Request(parameters=[param]))
            rclpy.spin_until_future_complete(node, fut, timeout_sec=5.0)
            if fut.result() is not None and all(r.successful for r in fut.result().results):
                done.add(full)
                failed.discard(full)
            else:
                failed.add(full)
            node.destroy_client(cli)
        time.sleep(1.0)
    print(f"[mavros_sim_time] use_sim_time=true on {len(done)} nodes under {prefix}"
          + (f"; FAILED: {sorted(failed)}" if failed else ""), flush=True)
    node.destroy_node()
    rclpy.shutdown()
    return 0 if f"{prefix}/time" in done else 1


if __name__ == "__main__":
    sys.exit(main())
