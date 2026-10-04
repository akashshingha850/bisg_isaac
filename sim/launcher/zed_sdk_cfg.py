"""
Stdlib-only half of the ZED SDK mode (zed_sdk_rig.py): decisions that launch.py has to make BEFORE Isaac Sim
starts (importing omni/isaacsim earlier crashes Kit), such as which Kit extension folder to register.
"""
import os

EXT_ID = "sl.sensor.camera"
BASE_PORT = 30000          # streaming port of drone 1; +2 per drone (ports must be even and unique)


def zed_source(zed_cfg: dict) -> str:
    """`emulated` (Isaac cameras publish the contract topics, zed_rig.py) or `sdk` (zed_sdk_rig.py). Scenario key
    `sensors.zed.source` wins over ZED_SOURCE (config/bisg.conf, exported by ./bisg)."""
    src = str(zed_cfg.get("source") or os.environ.get("ZED_SOURCE") or "emulated").strip().lower()
    if src not in ("emulated", "sdk"):
        raise SystemExit(f"[launch] sensors.zed.source / ZED_SOURCE must be emulated | sdk (got '{src}')")
    return src


def ext_folder() -> str:
    """Folder holding the built extension (docker/zed/build_isaac_ext.sh). Checked before Kit starts."""
    path = os.environ.get("ZED_ISAAC_EXT_DIR", "/workspace/docker/zed/zed-isaac-sim/exts")
    plugin = os.path.join(path, EXT_ID, "bin", "libsl.sensor.camera.plugin.so")
    if not os.path.isfile(plugin):
        raise SystemExit(f"[launch] ZED SDK mode needs the zed-isaac-sim extension, not found at {plugin}\n"
                         f"        build it once with:  ./bisg zed ext-build")
    return path


def stream_port(vehicle_id: int) -> int:
    return BASE_PORT + 2 * int(vehicle_id)
