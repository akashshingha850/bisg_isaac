"""
tf_relay: copy `<ns>/tf_static` (where the Isaac rig publishes its static ZED frames) to the global `/tf_static`.

tf2_ros listeners (cuVSLAM, rtabmap, rviz) subscribe to the ABSOLUTE topic `/tf_static`, so a per-drone namespaced
static tree is invisible to them. The real ZED wrapper has the same shape (frames prefixed `drone_<n>/`, one global
tf tree), so this relay also makes the sim look like the hardware. Transient-local both ways: late joiners get the tree.
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from tf2_msgs.msg import TFMessage


class TfRelay(Node):
    def __init__(self):
        super().__init__("tf_relay")
        self.declare_parameter("in_topic", "tf_static")     # relative: /<ns>/tf_static
        self.declare_parameter("out_topic", "/tf_static")
        qos = QoSProfile(depth=100, history=HistoryPolicy.KEEP_LAST, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                         reliability=ReliabilityPolicy.RELIABLE)
        out = self.get_parameter("out_topic").value
        self.pub = self.create_publisher(TFMessage, out, qos)
        self.create_subscription(TFMessage, self.get_parameter("in_topic").value, self._cb, qos)
        self.seen = set()
        self.get_logger().info(f"tf_relay: {self.get_parameter('in_topic').value} -> {out}")

    def _cb(self, msg: TFMessage):
        fresh = [t for t in msg.transforms if (t.header.frame_id, t.child_frame_id) not in self.seen]
        for t in fresh:
            self.seen.add((t.header.frame_id, t.child_frame_id))
        if fresh:
            self.pub.publish(TFMessage(transforms=fresh))


def main(args=None):
    rclpy.init(args=args)
    node = TfRelay()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
