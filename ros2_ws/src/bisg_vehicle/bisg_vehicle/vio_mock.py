#!/usr/bin/env python3
"""vio_mock — sim-only mock VIO source (docs/interface-contract.md, zed-contract skill).

Reads Pegasus ground truth (state/pose, state/twist — published by the ROS2Backend
`pub_state` on the vehicle, ENU/FLU) and republishes it, with injected Gaussian noise
and a fixed latency, as the vehicle's VIO estimate:

  {ns}/zed/zed_node/odom      -- "provided" (contract table: VIO source), frame_id/child_frame_id
                                 prefixed drone_<n>/ per interface-contract.md
  {ns}/mavros/odometry/out    -- "consumed" (MAVROS -> PX4 EKF2 external vision), frame_id/child_frame_id
                                 UNPREFIXED ("odom"/"base_link") — MAVROS's odom plugin only recognises
                                 its own fcu.odom_parent_id_des/odom_child_id_des ("odom"/"base_link",
                                 px4_config.yaml) and silently fails to fuse position/velocity on any
                                 other frame string. This is a MAVROS wiring requirement, not a contract
                                 violation: the contract fixes the frame hierarchy, not the literal string
                                 MAVROS is told to expect on its own input topic.
  TF {ns}/odom -> {ns}/base_link

Only this node and vio_relay (real hardware) may subscribe to ground truth (parity
rule, plan.md §8) — no other node should read state/pose or state/twist.

Simplification (documented, not hidden): odom is treated as coincident with map (no
drift model yet), so the "noisy VIO" position is ground truth + white noise, not a
driftful estimate. Revisit once real ZED Mini VIO characterises actual drift.
"""
import collections
import random

import rclpy
from geometry_msgs.msg import PoseStamped, TransformStamped, TwistStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from tf2_ros import TransformBroadcaster


class VioMock(Node):
    def __init__(self):
        super().__init__("vio_mock")

        self.declare_parameter("pos_noise_std", 0.01)   # metres, per-axis Gaussian
        self.declare_parameter("latency_s", 0.03)        # EKF2_EV_DELAY range: 30-80 ms (hardware.md)
        self.pos_noise_std = float(self.get_parameter("pos_noise_std").value)
        self.latency_s = float(self.get_parameter("latency_s").value)

        prefix = self.get_namespace().strip("/")
        self.frame_odom = f"{prefix}/odom" if prefix else "odom"
        self.frame_base = f"{prefix}/base_link" if prefix else "base_link"

        self._latest_twist = TwistStamped()
        self._queue = collections.deque()  # (enqueue_time_sec, Odometry) pending latency

        self.create_subscription(PoseStamped, "state/pose", self._on_pose, qos_profile_sensor_data)
        self.create_subscription(TwistStamped, "state/twist", self._on_twist, qos_profile_sensor_data)

        self.pub_zed = self.create_publisher(Odometry, "zed/zed_node/odom", qos_profile_sensor_data)
        # MAVROS's odom plugin subscribes reliable (mismatched reliability drops the whole
        # link silently — no error, just zero delivery), unlike our own sensor-QoS zed topic.
        mavros_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self.pub_mavros = self.create_publisher(Odometry, "mavros/odometry/out", mavros_qos)
        self.tf_broadcaster = TransformBroadcaster(self)

        self._drain_timer = self.create_timer(1.0 / 50.0, self._drain_queue)
        self.get_logger().info(
            f"vio_mock: {self.frame_odom} -> {self.frame_base}, "
            f"pos_noise_std={self.pos_noise_std} m, latency={self.latency_s * 1000:.0f} ms"
        )

    def _on_twist(self, msg: TwistStamped):
        self._latest_twist = msg

    def _on_pose(self, msg: PoseStamped):
        pos = (
            msg.pose.position.x + random.gauss(0.0, self.pos_noise_std),
            msg.pose.position.y + random.gauss(0.0, self.pos_noise_std),
            msg.pose.position.z + random.gauss(0.0, self.pos_noise_std),
        )
        # Diagonal-only covariance (row-major 6x6: x,y,z,rot_x,rot_y,rot_z). Zero/unset covariance
        # is a distinct, valid "unknown" signal to the consumer — reporting the real injected noise
        # instead avoids EKF2 either over-trusting a falsely-perfect measurement or (per EKF2_EV_NOISE_MD)
        # silently substituting its own lower-bound noise params.
        pos_var = self.pos_noise_std ** 2
        pose_cov = [0.0] * 36
        for i in (0, 7, 14):        # x,y,z diagonal
            pose_cov[i] = pos_var
        for i in (21, 28, 35):      # rot_x,rot_y,rot_z diagonal — orientation noise not modelled yet
            pose_cov[i] = 0.05

        self._queue.append((self.get_clock().now().nanoseconds / 1e9, msg.header.stamp, pos, msg.pose.orientation, pose_cov))

    def _drain_queue(self):
        now = self.get_clock().now().nanoseconds / 1e9
        while self._queue and (now - self._queue[0][0]) >= self.latency_s:
            _, stamp, pos, orientation, pose_cov = self._queue.popleft()
            twist = self._latest_twist.twist

            zed = Odometry()
            zed.header.stamp = stamp
            zed.header.frame_id = self.frame_odom
            zed.child_frame_id = self.frame_base
            zed.pose.pose.position.x, zed.pose.pose.position.y, zed.pose.pose.position.z = pos
            zed.pose.pose.orientation = orientation
            zed.pose.covariance = pose_cov
            zed.twist.twist.linear = twist.linear
            zed.twist.twist.angular = twist.angular
            self.pub_zed.publish(zed)

            # Same content, MAVROS-required frame names (see module docstring).
            mav = Odometry()
            mav.header.stamp = stamp
            mav.header.frame_id = "odom"
            mav.child_frame_id = "base_link"
            mav.pose.pose = zed.pose.pose
            mav.pose.covariance = pose_cov
            mav.twist.twist.linear = twist.linear
            mav.twist.twist.angular = twist.angular
            self.pub_mavros.publish(mav)

            t = TransformStamped()
            t.header.stamp = stamp
            t.header.frame_id = self.frame_odom
            t.child_frame_id = self.frame_base
            t.transform.translation.x, t.transform.translation.y, t.transform.translation.z = pos
            t.transform.rotation = orientation
            self.tf_broadcaster.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    node = VioMock()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
