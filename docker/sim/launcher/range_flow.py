"""
Downward ToF rangefinder + optical-flow sensor for a vehicle, fed straight to PX4 SITL (docs/range-flow.md).

Hardware being twinned (ultrahack2026 `compopnents.md`): Lightware LW20/C (downward, 5 cm..100 m) and PMW3901 flow.
On the real drone the flight controller reads both itself (serial / SPI), so the twin does the same: no ROS in the loop.
This is a Pegasus `Backend` that sits next to `PX4MavlinkBackend` and writes two MAVLink messages on the same simulator
link PX4 already reads HIL_SENSOR from (PX4 `SimulatorMavlink` turns them into `distance_sensor` / `sensor_optical_flow`):

  * ToF  -> DISTANCE_SENSOR   a PhysX ray from the sensor along body -Z; the nearest hit that is not the vehicle itself
  * flow -> HIL_OPTICAL_FLOW  integrated flow computed from the ground-truth body velocity and gyro at the sensor, divided
                              by the same ray length. Analytic, not image-based: it has the right scale, noise and
                              dropout behaviour, but no texture dependence (a featureless floor still "tracks").
  * ground truth -> HIL_STATE_QUATERNION (optional, `ground_truth:`) so PX4 logs `vehicle_*_groundtruth` on the same clock
                              as the sensors: what tests/range_flow_eval.py compares against. Pegasus has a sender for this
                              but never calls it, and its lat/lon/alt would only change at the GPS rate. PX4 does not use these
                              topics for estimation.

Flow convention = MAVLink's, which EKF2 negates on the way in (`EKF2.cpp`, "EKF uses the reverse sign convention to the flow
sensor"): sensor frame = body FRD, integrated flow = [-vy/d, +vx/d]*dt + the rotation about the sensor axes. EKF2 subtracts the
gyro it is given (`integrated_*gyro`), so the same rotation goes out in both fields.
"""
import logging

import numpy as np
from pegasus.simulator.logic.backends.backend import Backend
from scipy.spatial.transform import Rotation

LOG = logging.getLogger("launch")

MAV_DISTANCE_SENSOR_LASER = 0
MAV_SENSOR_ROTATION_PITCH_270 = 25      # downward facing
EARTH_R = 6371000.0                     # PX4 CONSTANTS_RADIUS_OF_EARTH (MapProjection)
GT_LAT0, GT_LON0 = 47.397742, 8.545594  # ground-truth reference (PX4's default home); any value works
GT_ALT0 = 100.0                         # m AMSL of world z = 0: ground-truth alt = GT_ALT0 + world z (tests/range_flow_eval.py)


def ned_to_latlon(north, east, lat0=GT_LAT0, lon0=GT_LON0):
    """Inverse of PX4's azimuthal-equidistant MapProjection, so PX4's ground-truth local x/y = world north/east."""
    la0, lo0 = np.radians(lat0), np.radians(lon0)
    c = np.hypot(north, east) / EARTH_R
    if c < 1e-12:
        return lat0, lon0
    sc, cc = np.sin(c), np.cos(c)
    lat = np.arcsin(cc * np.sin(la0) + north * sc * np.cos(la0) / (c * EARTH_R))
    lon = lo0 + np.arctan2(east * sc, c * EARTH_R * np.cos(la0) * cc - north * np.sin(la0) * sc)
    return np.degrees(lat), np.degrees(lon)


class RangeFlowBackend(Backend):
    """cfg: the vehicle's `sensors:` block (`tof:` and/or `optical_flow:`); px4: the vehicle's PX4MavlinkBackend."""

    def __init__(self, px4, cfg):
        super().__init__(None)
        self._px4 = px4
        tof, flow, gt = cfg.get("tof") or {}, cfg.get("optical_flow") or {}, cfg.get("ground_truth") or {}
        self.tof_on, self.flow_on = bool(tof.get("enabled", False)), bool(flow.get("enabled", False))
        self.gt_on = bool(gt.get("enabled", False))
        self._gt_dt = 1.0 / float(gt.get("rate_hz", 100.0))
        self._gt_acc = 0.0
        self._rng = np.random.default_rng(int(cfg.get("seed", 0)) or None)

        # ToF (LW20/C: 5 cm .. 100 m, ~1 cm resolution)
        self._tof_mount = np.array(tof.get("mount_xyz", [0.0, 0.0, -0.05]), dtype=float)   # base_link FLU, m
        self._tof_min, self._tof_max = float(tof.get("min_m", 0.05)), float(tof.get("max_m", 100.0))
        self._tof_dt = 1.0 / float(tof.get("rate_hz", 50.0))
        self._tof_noise = float(tof.get("noise_std_m", 0.01))
        # flow (PMW3901: works from 8 cm; quality falls to 0 beyond ~5 m)
        self._flow_mount = np.array(flow.get("mount_xyz", [0.0, 0.0, -0.05]), dtype=float)
        self._flow_min, self._flow_max = float(flow.get("min_m", 0.08)), float(flow.get("max_m", 5.0))
        self._flow_dt = 1.0 / float(flow.get("rate_hz", 50.0))
        self._flow_noise = float(flow.get("noise_std_rad_s", 0.02))
        self._quality = int(flow.get("quality", 255))

        self._state = None
        self._t = 0.0
        self._tof_acc = self._flow_acc = 0.0
        self._flow_gyro = np.zeros(3)      # FRD gyro integrated since the last flow message, rad
        self._flow_span = 0.0
        self.last_range = None             # most recent ToF reading, m (None = no hit) - for logs and tests
        self.sent = {"tof": 0, "flow": 0, "gt": 0}
        self._query = None
        self._warned = False
        self._logged = 0

    # ---- Backend interface --------------------------------------------------------------------------------------
    def update_sensor(self, sensor_type, data):
        pass

    def update_graphical_sensor(self, sensor_type, data):
        pass

    def update_state(self, state):
        self._state = state

    def input_reference(self):
        return []

    def start(self):
        self._query = None

    def stop(self):
        pass

    def reset(self):
        self._t = self._tof_acc = self._flow_acc = self._flow_span = self._gt_acc = 0.0
        self._flow_gyro[:] = 0.0

    def update(self, dt):
        conn = getattr(self._px4, "_connection", None)
        if self._state is None or conn is None or not getattr(self._px4, "_received_first_hearbeat", False):
            return
        self._t += dt
        self._tof_acc += dt
        self._flow_acc += dt
        if self.flow_on:
            self._flow_span += dt
            self._flow_gyro += self._gyro_frd() * dt
        if self.tof_on and self._tof_acc >= self._tof_dt:
            self._tof_acc -= self._tof_dt
            self._send_tof(conn)
        if self.flow_on and self._flow_acc >= self._flow_dt:
            self._flow_acc -= self._flow_dt
            self._send_flow(conn)
        if self.gt_on:
            self._gt_acc += dt
            if self._gt_acc >= self._gt_dt:
                self._gt_acc -= self._gt_dt
                self._send_ground_truth(conn)

    # ---- geometry -----------------------------------------------------------------------------------------------
    def _gyro_frd(self):
        p, q, r = self._state.angular_velocity          # FLU body
        return np.array([p, -q, -r])

    def _ray(self, mount):
        """Range from `mount` (body FLU) straight down the body Z axis to the first collider that is not the vehicle."""
        s = self._state
        rot = Rotation.from_quat(s.attitude)
        origin = np.asarray(s.position) + rot.apply(mount)
        down = rot.apply([0.0, 0.0, -1.0])
        if self._query is None:
            from omni.physx import get_physx_scene_query_interface  # noqa: WPS433
            self._query = get_physx_scene_query_interface()
        import carb  # noqa: WPS433
        own = self.vehicle.prim_path if self.vehicle is not None else ""
        best = [None]
        seen = []

        def report(hit):
            path = getattr(hit, "collision", "") or getattr(hit, "rigid_body", "") or ""
            seen.append((path, round(float(hit.distance), 3)))
            if own and path.startswith(own):
                return True                              # the airframe itself: keep looking
            if best[0] is None or hit.distance < best[0]:
                best[0] = float(hit.distance)
            return True

        try:
            self._query.raycast_all(carb.Float3(*[float(x) for x in origin]), carb.Float3(*[float(x) for x in down]),
                                    float(max(self._tof_max, self._flow_max)), report, False)
            if self._logged < 3:                          # one-off: what the first rays hit (diagnoses a floor without collider)
                self._logged += 1
                LOG.info("ray from %s down %s: %d hit(s) %s", np.round(origin, 3), np.round(down, 2), len(seen), seen[:4])
        except Exception as exc:  # noqa: BLE001 - a sensor must never stop the sim
            if not self._warned:
                LOG.warning("raycast failed (%s); ToF/flow report no range", exc)
                self._warned = True
            return None
        return best[0]

    # ---- messages -----------------------------------------------------------------------------------------------
    def _send_tof(self, conn):
        d = self._ray(self._tof_mount)
        if d is not None:
            d = d + self._rng.normal(0.0, self._tof_noise)
        ok = d is not None and self._tof_min <= d <= self._tof_max
        self.last_range = d if ok else None
        # no hit / out of range: report just past max (PX4 rejects a reading outside [min, max])
        cm = int(round(d * 100)) if ok else int(round(self._tof_max * 100)) + 1
        try:
            conn.mav.distance_sensor_send(
                int(self._t * 1000) & 0xFFFFFFFF, int(self._tof_min * 100), int(self._tof_max * 100), min(cm, 65535),
                MAV_DISTANCE_SENSOR_LASER, 0, MAV_SENSOR_ROTATION_PITCH_270, 0)
            self.sent["tof"] += 1
        except Exception:  # noqa: BLE001
            pass

    def _send_flow(self, conn):
        s = self._state
        d = self._ray(self._flow_mount)
        span, gyro = self._flow_span, self._flow_gyro.copy()
        self._flow_span, self._flow_gyro[:] = 0.0, 0.0
        if span <= 0.0:
            return
        valid = d is not None and self._flow_min <= d <= self._flow_max
        if valid:
            # velocity of the sensor point, body FLU -> FRD
            v = np.asarray(s.linear_body_velocity) + np.cross(s.angular_velocity, self._flow_mount)
            vx, vy = v[0], -v[1]
            gx, gy, gz = gyro / span                     # mean FRD rates over the span
            fx = -vy / d + gx + self._rng.normal(0.0, self._flow_noise)
            fy = vx / d + gy + self._rng.normal(0.0, self._flow_noise)
            quality, dist = self._quality, d
        else:
            fx = fy = 0.0
            quality, dist = 0, -1.0                      # negative = distance unknown
        try:
            conn.mav.hil_optical_flow_send(
                int(self._t * 1e6), 0, int(span * 1e6), fx * span, fy * span,
                float(gyro[0]), float(gyro[1]), float(gyro[2]), 0, quality, 0, dist)
            self.sent["flow"] += 1
        except Exception:  # noqa: BLE001
            pass

    def _send_ground_truth(self, conn):
        s = self._state
        x, y, z, w = s.get_attitude_ned_frd()            # scipy order -> MAVLink [w, x, y, z]
        p, q, r = s.get_angular_velocity_frd()
        vn, ve, vd = s.get_linear_velocity_ned()
        an, ae, ad = s.get_linear_acceleration_ned()
        lat, lon = ned_to_latlon(float(s.position[1]), float(s.position[0]))   # world ENU: north = y, east = x
        try:
            conn.mav.hil_state_quaternion_send(
                int(self._t * 1e6), [float(w), float(x), float(y), float(z)], float(p), float(q), float(r),
                int(round(lat * 1e7)), int(round(lon * 1e7)), int(round((GT_ALT0 + float(s.position[2])) * 1000)),
                int(round(vn * 100)), int(round(ve * 100)), int(round(vd * 100)), 0, 0,
                int(round(an * 1000)), int(round(ae * 1000)), int(round(ad * 1000)))
            self.sent["gt"] += 1
        except Exception:  # noqa: BLE001
            pass


def attach(vehicle_cfg, px4_backend):
    """Return a RangeFlowBackend for a scenario vehicle, or None when neither sensor is enabled."""
    sensors = vehicle_cfg.get("sensors") or {}
    if not any((sensors.get(k) or {}).get("enabled", False) for k in ("tof", "optical_flow", "ground_truth")):
        return None
    return RangeFlowBackend(px4_backend, sensors)
