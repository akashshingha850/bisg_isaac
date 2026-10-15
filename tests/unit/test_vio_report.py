"""VIO campaign report + verdict (tests/vio_report.py), numpy only, any PC: python3 -m unittest tests.unit.test_vio_report -v

Builds small campaign dirs the way tests/vio_campaign.py writes them, from the archived 2026-10-15 flights
(archive/vio-2026-10-15), and checks the verdict logic, the calibration suggestions, the files and the SVG figures.
"""
import csv
import json
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "tests"))
import vio_eval  # noqa: E402
import vio_report  # noqa: E402

ARCHIVE = os.path.join(ROOT, "archive", "vio-2026-10-15")
VERIFY = {"latency_abs_ms": 20, "vel_scale_err": 0.03, "lever_arm_m": 0.03, "event_free_horiz_max_m": 0.25,
          "performance_horiz_max_m": 0.30}
_CACHE = {}


def dump(obj, path):
    with open(path, "w") as fh:
        json.dump(obj, fh)


def load(path):
    with open(path) as fh:
        return json.load(fh)


def evaluated(run):
    if run not in _CACHE:
        path = os.path.join(ARCHIVE, run, "topics.npz")
        if not os.path.exists(path):
            raise unittest.SkipTest(f"{path} missing")
        _CACHE[run] = vio_eval.analyse(vio_eval.load(path))
    return _CACHE[run]


def campaign(tmp, flights, infra=()):
    """flights: [(config, rep, archived run)]; infra: [(config, rep)] that never flew."""
    names = list(dict.fromkeys(c for c, _, _ in flights))
    plan = {"scenario": "default", "view": "headless", "reps": 2, "flight_args": "", "verify": VERIFY, "selected_configs": names,
            "configs": {n: {"about": n, "params": {} if n == "calibrated" else {"MC_YAWRATE_MAX": 200.0}} for n in names}}
    dump(plan, os.path.join(tmp, "campaign.json"))
    dump({"host": "test", "os": "x", "kernel": "x", "cpu": "x", "cpu_threads": 1, "ram_gb": 1, "gpus": ["x"], "docker": "x",
               "git_branch": "b", "git_commit": "c", "git_dirty": False, "pegasus_commit": "p"}, os.path.join(tmp, "machine.json"))
    for c, k, run in flights:
        d = os.path.join(tmp, "runs", f"{c}-r{k}")
        os.makedirs(d)
        rep, _, ser = evaluated(run)
        dump(rep, os.path.join(d, "vio_eval.json"))
        if ser is not None:
            vio_eval.write_series(ser, os.path.join(d, "series.csv"))
        dump({"config": c, "rep": k, "status": "done", "attempts": 1, "flight_rc": 0, "rtf": {"median": 0.57},
                   "infra_failures": [], "versions": {"px4": "v1.17.0"}}, os.path.join(d, "run.json"))
    for c, k in infra:
        d = os.path.join(tmp, "runs", f"{c}-r{k}")
        os.makedirs(d)
        dump({"config": c, "rep": k, "status": "infra_failed",
                   "infra_failures": [{"attempt": 1, "what": "zed wrapper crashed (R9)"}]}, os.path.join(d, "run.json"))
    return tmp


class Report(unittest.TestCase):
    def test_calibrated_campaign_passes_and_writes_everything(self):
        with tempfile.TemporaryDirectory() as tmp:
            campaign(tmp, [("calibrated", 1, "3-yawrate60-eva001-live"), ("px4_defaults", 1, "1-baseline"),
                           ("calibrated", 2, "4-confirm-fromfile")], infra=[("px4_defaults", 2)])
            self.assertEqual(vio_report.build(tmp, quiet=True), "PASS")
            s = load(os.path.join(tmp, "summary.json"))
            self.assertEqual(s["stats"]["calibrated"]["ekf_h_max"]["n"], 2)
            self.assertAlmostEqual(s["stats"]["px4_defaults"]["ekf_h_max"]["mean"], 0.41, delta=0.03)
            self.assertTrue(any("restamp_latency_ms" in x for x in s["suggestions"]))        # +10 ms residual -> 85 -> 95
            self.assertEqual(s["attribution"]["calibrated"]["none (drift)"], 1)              # run 3
            self.assertEqual(s["attribution"]["calibrated"]["slip at a frame gap"], 1)       # run 4: 0.22 m at a 383 ms gap
            for part in ("## Performance and failure attribution", "Event-free flights only"):
                with open(os.path.join(tmp, "summary.md")) as fh:
                    self.assertIn(part, fh.read())
            with open(os.path.join(tmp, "summary.md")) as fh:
                md = fh.read()
            for part in ("## Experimental setup", "## Results", "## Ablation", "## Calibration", "## Reliability", "zed wrapper crashed"):
                self.assertIn(part, md)
            with open(os.path.join(tmp, "summary.csv")) as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(len(rows), 4)
            figs = os.listdir(os.path.join(tmp, "figures"))
            self.assertEqual(len(figs), len(vio_report.FIGS) + 2)
            for f in figs:
                ET.parse(os.path.join(tmp, "figures", f))                                   # well-formed SVG

    def test_only_event_flights_cannot_verify_the_calibration(self):
        with tempfile.TemporaryDirectory() as tmp:
            campaign(tmp, [("calibrated", 1, "1-baseline")])                       # 0.41 m from a yaw slip at a frame gap
            self.assertEqual(vio_report.build(tmp, quiet=True), "FAIL")
            s = load(os.path.join(tmp, "summary.json"))
            self.assertEqual(s["flights"][0]["event"], "yaw slip at a frame gap")
            check = next(c for c in s["checks"] if c["check"].startswith("event-free calibrated"))
            self.assertFalse(check["pass"])
            self.assertIn("none", check["value"])

    def test_error_without_an_sdk_event_fails_the_verdict(self):
        """A drifting estimate with a clean ZED = a configuration fault (not the SDK): the calibration verdict must fail."""
        from tests.unit.test_vio_eval import flight
        with tempfile.TemporaryDirectory() as tmp:
            campaign(tmp, [("calibrated", 1, "3-yawrate60-eva001-live")])
            d = flight()
            lp = d["vehicle_local_position"]
            lp["x"] = lp["x"] + 0.006 * (lp["timestamp"] / 1e6)                     # EKF2 drifts 0.35 m, the ZED does not
            rep, _, ser = vio_eval.analyse(d)
            self.assertEqual(rep["dominant_event"], "none (drift)")
            run = os.path.join(tmp, "runs", "calibrated-r1")
            dump(rep, os.path.join(run, "vio_eval.json"))
            vio_eval.write_series(ser, os.path.join(run, "series.csv"))
            self.assertEqual(vio_report.build(tmp, quiet=True), "FAIL")

    def test_nothing_flown_is_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            campaign(tmp, [], infra=[("calibrated", 1)])
            os.makedirs(os.path.join(tmp, "figures"), exist_ok=True)
            plan = load(os.path.join(tmp, "campaign.json"))
            plan["selected_configs"] = ["calibrated"]
            plan["configs"] = {"calibrated": {"about": "", "params": {}}}
            dump(plan, os.path.join(tmp, "campaign.json"))
            self.assertEqual(vio_report.build(tmp, quiet=True), "INCOMPLETE")

    def test_campaign_config_is_complete(self):
        import yaml
        with open(os.path.join(ROOT, "tests", "vio_bench.yaml")) as fh:
            cfg = yaml.safe_load(fh)
        self.assertIn("calibrated", cfg["default_configs"])
        for n in cfg["default_configs"]:
            self.assertIn(n, cfg["configs"])
        self.assertEqual(set(cfg["verify"]), set(VERIFY))


if __name__ == "__main__":
    unittest.main()
