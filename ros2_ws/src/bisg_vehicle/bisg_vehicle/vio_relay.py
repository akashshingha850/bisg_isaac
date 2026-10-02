"""
vio_relay: turn ANY visual-odometry source into the vehicle contract (docs/interface-contract.md, docs/perception.md).

    perception/odom  (nav_msgs/Odometry from cuVSLAM, rtabmap, the ZED wrapper ...)
        -> zed/zed_node/odom       drone_<n>/-prefixed frames, sensor QoS            (optional, `publish_zed_odom`)
        -> mavros/odometry/out     UNPREFIXED odom/base_link frames, reliable QoS     (optional, `feed_mavros`)
        -> tf drone_<n>/odom -> drone_<n>/base_link                                   (optional, `publish_tf`)

The frame/QoS rules are the ones vio_mock learned the hard way (see its docstring): MAVROS's odom plugin only matches the
literal frame names `odom`/`base_link`, and subscribes reliable. `feed_mavros:=false` is the observer mode used by the
benchmark: the backend is evaluated on a flight that the mock is flying, without influencing it.

Real drone: the same node with `in_topic:=zed/zed_node/odom publish_zed_odom:=false` re-parents the ZED wrapper's odometry.
Covariance: a missing (all-zero) covariance is replaced by `default_pos_std` / `default_rot_std`, because zero tells EKF2
"unknown" and it then substitutes its own, possibly over-optimistic, noise parameters.
"""
import rclpy
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from tf2_ros import TransformBroadcaster


class VioRelay(Node):
    def __init__(self):
        super().__init__("vio_relay")
        self.declare_parameter("in_topic", "perception/odom")
        self.declare_parameter("feed_mavros", True)
        self.declare_parameter("publish_zed_odom", True)
        self.declare_parameter("publish_tf", True)
        self.declare_parameter("default_pos_std", 0.02)   # m
        self.declare_parameter("default_rot_std", 0.05)   # rad
        g = lambda n: self.get_parameter(n).value  # noqa: E731
        self.feed_mavros, self.pub_zed_on, self.pub_tf_on = bool(g("feed_mavros")), bool(g("publish_zed_odom")), bool(g("publish_tf"))
        self.pos_var, self.rot_var = float(g("default_pos_std")) ** 2, float(g("default_rot_std")) ** 2

        prefix = self.get_namespace().strip("/")
        self.frame_odom = f"{prefix}/odom" if prefix else "odom"
        self.frame_base = f"{prefix}/base_link" if prefix else "base_link"

        self.create_subscription(Odometry, str(g("in_topic")), self._on_odom, qos_profile_sensor_data)
        self.pub_zed = self.create_publisher(Odometry, "zed/zed_node/odom", qos_profile_sensor_data) if self.pub_zed_on else None
        self.pub_mavros = (self.create_publisher(Odometry, "mavros/odometry/out", QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE))
                           if self.feed_mavros else None)
        self.tf = TransformBroadcaster(self) if self.pub_tf_on else None
        self.n = 0
        self.get_logger().info(f"vio_relay: {g('in_topic')} -> zed_odom={self.pub_zed_on} mavros={self.feed_mavros} tf={self.pub_tf_on}")

    def _covariance(self, msg):
        cov = list(msg.pose.covariance)
        if any(cov):
            return cov
        cov = [0.0] * 36
        for i in (0, 7, 14):
            cov[i] = self.pos_var
        for i in (21, 28, 35):
            cov[i] = self.rot_var
        return cov

    def _on_odom(self, msg: Odometry):
        cov = self._covariance(msg)
        self.n += 1
        if self.pub_zed is not None:
            out = Odometry()
            out.header.stamp = msg.header.stamp
            out.header.frame_id, out.child_frame_id = self.frame_odom, self.frame_base
            out.pose.pose, out.pose.covariance, out.twist = msg.pose.pose, cov, msg.twist
            self.pub_zed.publish(out)
        if self.pub_mavros is not None:
            out = Odometry()
            out.header.stamp = msg.header.stamp
            out.header.frame_id, out.child_frame_id = "odom", "base_link"
            out.pose.pose, out.pose.covariance, out.twist = msg.pose.pose, cov, msg.twist
            self.pub_mavros.publish(out)
        if self.tf is not None:
            t = TransformStamped()
            t.header.stamp = msg.header.stamp
            t.header.frame_id, t.child_frame_id = self.frame_odom, self.frame_base
            p, q = msg.pose.pose.position, msg.pose.pose.orientation
            t.transform.translation.x, t.transform.translation.y, t.transform.translation.z = p.x, p.y, p.z
            t.transform.rotation = q
            self.tf.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    node = VioRelay()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
