"""./bisg px4-bridge: one compose service (px4-bridge), PX4_BRIDGE picks what its entrypoint runs. Checked with `plan` / `up` argument
handling, the compose model and the entrypoint's dispatch (no container is started).

    python3 -m unittest tests.unit.test_px4_bridge_cli        (from the repo root)
"""
import json
import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COMPOSE = os.path.join(ROOT, "docker", "compose.yaml")
ENTRYPOINT = os.path.join(ROOT, "docker", "px4-bridge", "entrypoint.sh")


def bridge(*args, **env):
    r = subprocess.run([os.path.join(ROOT, "bisg"), "px4-bridge", *args], capture_output=True, text=True,
                       env=dict(os.environ, **env), timeout=60)
    return r.returncode, r.stdout + r.stderr


def compose_service(**env):
    env = dict(os.environ, **env)
    env.pop("PX4_BRIDGE", None) if "PX4_BRIDGE" not in env else None
    r = subprocess.run(["docker", "compose", "-f", COMPOSE, "--profile", "px4-bridge", "config", "--format", "json"],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)["services"]


class Px4BridgeCli(unittest.TestCase):
    def test_default_is_mavros(self):
        rc, out = bridge("plan", PX4_BRIDGE="mavros")
        self.assertEqual(rc, 0)
        self.assertRegex(out, r"\n  mavros\s+MAVLink")
        self.assertIn("/drone_1/mavros/", out)

    def test_variable_picks_the_bridge(self):
        for name, marker in (("mavsdk", "gRPC localhost:50051"), ("xrce", "/fmu/in|out/"), ("none", "nothing")):
            rc, out = bridge("plan", PX4_BRIDGE=name)
            self.assertEqual(rc, 0)
            self.assertRegex(out, rf"\n  {name}\s")
            self.assertIn(marker, out)

    def test_several_bridges_at_once(self):
        rc, out = bridge("plan", "--drone", "2", PX4_BRIDGE="mavros,xrce")
        self.assertIn("mavros MAVLink udp://:14541@127.0.0.1:14581", out)
        self.assertIn("xrce   XRCE udp4", out)

    def test_mavros_and_mavsdk_cannot_share_the_mavlink_port(self):
        rc, out = bridge("up", PX4_BRIDGE="mavros,mavsdk")
        self.assertNotEqual(rc, 0)
        self.assertIn("cannot run together", out)

    def test_on_the_drone_only_one_bridge_owns_the_serial_port(self):
        rc, out = bridge("up", "--hw", "mavros", "xrce")
        self.assertNotEqual(rc, 0)
        self.assertIn("cannot run together", out)

    def test_name_argument_overrides_the_variable_for_one_run(self):
        rc, out = bridge("plan", "xrce", PX4_BRIDGE="mavros")
        self.assertRegex(out, r"\n  xrce\s+XRCE")
        self.assertNotIn("mavros", out.split("\n", 1)[1])

    def test_bad_value_is_rejected(self):
        rc, out = bridge("plan", PX4_BRIDGE="dds")
        self.assertNotEqual(rc, 0)
        self.assertIn("PX4_BRIDGE: 'dds'", out)
        rc, out = bridge("up", "px4flow")
        self.assertNotEqual(rc, 0)

    def test_drone_number_moves_the_ports(self):
        rc, out = bridge("plan", "mavsdk", "--drone", "3")
        self.assertIn("udpin://0.0.0.0:14542", out)       # PX4 instance 2 -> 14540 + 2

    def test_hw_uses_the_serial_port(self):
        _, mav = bridge("plan", "mavros", "--hw")
        _, xrce = bridge("plan", "xrce", "--hw")
        self.assertIn("serial:///dev/px4:921600", mav)
        self.assertIn("XRCE serial /dev/px4", xrce)

    def test_params_differ_per_bridge(self):
        _, mav = bridge("params", "mavros")
        _, xrce = bridge("params", "xrce")
        self.assertIn("MAV_1_MODE", mav)
        self.assertRegex(mav, r"UXRCE_DDS_CFG\s+Disabled")
        self.assertRegex(xrce, r"UXRCE_DDS_CFG\s+TELEM 2")
        self.assertRegex(xrce, r"MAV_1_CONFIG\s+Disabled")
        _, xrce3 = bridge("params", "xrce", "--drone", "7")
        self.assertRegex(xrce3, r"UXRCE_DDS_NS_IDX\s+7 ")      # the drone id is the topic namespace index

    def test_one_service_with_an_entrypoint_and_no_command(self):
        svc = compose_service()
        bridges = [n for n in svc if "bridge" in n and not n.startswith("zed")]
        self.assertEqual(bridges, ["px4-bridge"])
        s = svc["px4-bridge"]
        self.assertEqual(s["entrypoint"], ["/workspace/docker/px4-bridge/entrypoint.sh"])
        self.assertIn(s.get("command"), (None, []))        # compose prints command: null once entrypoint is overridden; none is set
        self.assertEqual(s["environment"]["PX4_BRIDGE"], "mavros")           # raw-compose default
        self.assertEqual(s["container_name"], "bisg-mavros-1")               # one container per bridge and drone

    def test_compose_passes_the_variable_through(self):
        s = compose_service(PX4_BRIDGE="xrce", DRONE_ID="3")["px4-bridge"]
        self.assertEqual(s["environment"]["PX4_BRIDGE"], "xrce")
        self.assertEqual(s["container_name"], "bisg-xrce-3")

    def test_entrypoint_dispatch(self):          # needs the image (ROS is sourced inside the container): skipped where it is not built
        if subprocess.run(["docker", "image", "inspect", "bisg/px4-bridge:jazzy"], capture_output=True).returncode != 0:
            self.skipTest("bisg/px4-bridge:jazzy not built (./bisg px4-bridge build)")

        def run(**env):
            cmd = ["docker", "run", "--rm", "-v", f"{ROOT}:/workspace:ro", "--entrypoint", "/workspace/docker/px4-bridge/entrypoint.sh"]
            for k, v in env.items():
                cmd += ["-e", f"{k}={v}"]
            r = subprocess.run(cmd + ["bisg/px4-bridge:jazzy"], capture_output=True, text=True, timeout=60)
            return r.returncode, r.stdout + r.stderr
        rc, out = run(PX4_BRIDGE="none")
        self.assertEqual(rc, 0)
        self.assertIn("nothing to run", out)
        rc, out = run(PX4_BRIDGE="dds")
        self.assertEqual(rc, 2)
        self.assertIn("is not mavros | mavsdk | xrce | none", out)


if __name__ == "__main__":
    unittest.main()
