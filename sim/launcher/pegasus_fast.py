"""
Per-step speed-ups for Pegasus on Isaac Sim 6.0 (docs/performance.md, migration-errors.md M8), applied at runtime so the
pinned docker/sim/PegasusSimulator checkout stays untouched.

The Pegasus PR #144 port builds a brand-new `RigidPrim` wrapper (prim lookup + physics-tensor view) for every rotor on
every physics step, and writes every propeller joint velocity every step even when it did not change. With the Python
loop being the sim's bottleneck (one thread, GPU idle) that is most of the step time.

  * Vehicle.apply_force / apply_torque: cache one RigidPrim per body part (dropped when the sim stops).
  * Multirotor.handle_propeller_visual: write the joint velocity only when the value changes.
  * Multirotor.update: the 4 rotor forces, the body torque and the body drag go out in ONE tensor call (one RigidPrim over
    body + 4 rotors) instead of six - each call costs ~0.35 ms of warp-array building, six per step.

Same forces, same torques, same visuals. Switch off with `perf.pegasus_fast: false`.
"""
import logging

import numpy as np

LOG = logging.getLogger("launch")


def apply():
    from isaacsim.core.experimental.prims import RigidPrim  # noqa: WPS433
    from pegasus.simulator.logic.vehicles.multirotor import Multirotor  # noqa: WPS433
    from pegasus.simulator.logic.vehicles.vehicle import Vehicle  # noqa: WPS433

    def _prim(self, body_part):
        body = self._body_rigid_prim
        if body_part == "/body":
            return body
        cache = self.__dict__.setdefault("_bisg_prims", {})
        if cache.get("_owner") is not body:      # a new body prim = the sim was restarted: rebuild
            cache.clear()
            cache["_owner"] = body
        if body_part not in cache:
            cache[body_part] = RigidPrim(paths=self._stage_prefix + body_part)
        return cache[body_part]

    def apply_force(self, force, pos=(0.0, 0.0, 0.0), body_part="/body"):
        if self._body_rigid_prim is None or not self._body_rigid_prim.is_physics_tensor_entity_valid():
            return
        forces = np.array([[force[0], force[1], force[2]]], dtype=np.float32)
        torques = np.zeros((1, 3), dtype=np.float32)
        positions = np.array([[pos[0], pos[1], pos[2]]], dtype=np.float32)
        _prim(self, body_part).apply_forces_and_torques_at_pos(
            forces=forces, torques=torques, positions=positions, local_frame=True)

    def apply_torque(self, torque, body_part="/body"):
        if self._body_rigid_prim is None or not self._body_rigid_prim.is_physics_tensor_entity_valid():
            return
        forces = np.zeros((1, 3), dtype=np.float32)
        torques = np.array([[torque[0], torque[1], torque[2]]], dtype=np.float32)
        positions = np.zeros((1, 3), dtype=np.float32)
        _prim(self, body_part).apply_forces_and_torques_at_pos(
            forces=forces, torques=torques, positions=positions, local_frame=True)

    orig_visual = Multirotor.handle_propeller_visual

    def handle_propeller_visual(self, rotor_number, force):
        if 0.0 < force < 0.1:
            state = 1
        elif force >= 0.1:
            state = 2
        else:
            state = 0
        last = self.__dict__.setdefault("_bisg_prop_state", {})
        if last.get(rotor_number) == state and self._articulation is not None:
            return                                # same spin state as last step: nothing to write
        orig_visual(self, rotor_number, force)
        if self._articulation is not None and self._articulation.is_physics_tensor_entity_valid():
            last[rotor_number] = state

    # a stop() drops the articulation: forget the spin state so the next start writes it again
    orig_stop = Multirotor.stop

    def stop(self):
        self.__dict__.pop("_bisg_prop_state", None)
        orig_stop(self)

    orig_update = Multirotor.update

    def update(self, dt, context=None):
        body = self._body_rigid_prim
        if body is None or not body.is_physics_tensor_entity_valid() or self._thrusters is None:
            return orig_update(self, dt, context)
        batch = self.__dict__.get("_bisg_batch")
        if batch is None or batch[0] is not body:
            paths = [self._stage_prefix + "/body"] + [self._stage_prefix + f"/rotor{i}" for i in range(4)]
            batch = self.__dict__["_bisg_batch"] = (body, RigidPrim(paths=paths))
        view = batch[1]

        desired = self._backends[0].input_reference() if len(self._backends) != 0 else [0.0] * self._thrusters._num_rotors
        self._thrusters.set_input_reference(desired)
        forces_z, _, rolling_moment = self._thrusters.update(self._state, dt)
        drag = self._drag.update(self._state, dt)

        forces = np.zeros((5, 3), dtype=np.float32)
        torques = np.zeros((5, 3), dtype=np.float32)
        forces[0] = drag                         # body: linear drag + yaw reaction torque
        torques[0, 2] = rolling_moment
        forces[1:, 2] = forces_z[:4]             # rotors: thrust along the rotor z axis
        view.apply_forces_and_torques_at_pos(forces=forces, torques=torques, positions=np.zeros((5, 3), np.float32),
                                             local_frame=True)
        for i in range(4):
            self.handle_propeller_visual(i, forces_z[i])
        for backend in self._backends:
            backend.update(dt)

    Multirotor.update = update
    Vehicle.apply_force = apply_force
    Vehicle.apply_torque = apply_torque
    Multirotor.handle_propeller_visual = handle_propeller_visual
    Multirotor.stop = stop
    LOG.info("pegasus_fast: cached RigidPrim wrappers + change-only propeller visuals")
