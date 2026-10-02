"""
One launch file, two interchangeable perception backends (docs/perception.md).

    ros2 launch bisg_perception perception.launch.py backend:=isaac_ros   # Isaac ROS 4.6: cuVSLAM + VPI SGM (GPU, NITROS)
    ros2 launch bisg_perception perception.launch.py backend:=ros2        # traditional CPU: rtabmap stereo odom + stereo_image_proc

Both read the sim's / the ZED wrapper's contract topics (zed/zed_node/{left,right}/image_rect_color, camera_info, imu/data)
inside the /drone_<id> namespace and publish the SAME backend interface:

    perception/odom        nav_msgs/Odometry   (odom -> base_link, visual or visual-inertial odometry)
    perception/disparity   stereo_msgs/DisparityImage

`vio_relay` then maps perception/odom onto the vehicle contract (zed/zed_node/odom, mavros/odometry/out, tf).
Arguments:  confidence/max_disparity (isaac_ros disparity)  drone_id  feed_mavros (false = observer mode, used by the benchmark)  odom (true|false)  depth (true|false)
            imu (cuVSLAM only: fuse the IMU)  use_sim_time
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode

LEFT, RIGHT = "zed/zed_node/left", "zed/zed_node/right"


def _b(ctx, name):
    return LaunchConfiguration(name).perform(ctx).lower() in ("1", "true", "yes", "on")


def _nodes(context, *_, **__):
    backend = LaunchConfiguration("backend").perform(context)
    drone = int(LaunchConfiguration("drone_id").perform(context))
    ns = f"drone_{drone}"
    sim_time = _b(context, "use_sim_time")
    want_odom, want_depth, imu = _b(context, "odom"), _b(context, "depth"), _b(context, "imu")
    frames = {"base": f"{ns}/base_link", "imu": f"{ns}/zed_imu_link",
              "left": f"{ns}/zed_left_camera_optical_frame", "right": f"{ns}/zed_right_camera_optical_frame"}

    actions = [
        Node(package="bisg_perception", executable="tf_relay", namespace=ns, name="tf_relay", output="screen",
             parameters=[{"use_sim_time": sim_time}]),
        Node(package="bisg_vehicle", executable="vio_relay", namespace=ns, name="vio_relay", output="screen",
             parameters=[{"use_sim_time": sim_time, "in_topic": "perception/odom",
                          "feed_mavros": _b(context, "feed_mavros"), "publish_zed_odom": True, "publish_tf": True}]),
    ]
    composables, container = [], "component_container_mt"

    if backend == "isaac_ros":
        if want_odom:
            vslam = {
                "use_sim_time": sim_time, "rectified_images": True, "enable_image_denoising": False,
                "base_frame": frames["base"], "camera_optical_frames": [frames["left"], frames["right"]],
                "publish_map_to_odom_tf": False, "publish_odom_to_base_tf": False,
                "enable_slam_visualization": False, "enable_landmarks_view": False, "enable_observations_view": False,
                "image_jitter_threshold_ms": 80.0,
            }
            if imu:   # VIO: needs the IMU frame in TF and plausible noise densities (sim IMU is noiseless; small values)
                vslam.update({"tracking_mode": 1, "imu_frame": frames["imu"], "calibration_frequency": 200.0,
                              "gyro_noise_density": 0.0002, "gyro_random_walk": 0.00002,
                              "accel_noise_density": 0.002, "accel_random_walk": 0.003})
            remaps = [("visual_slam/image_0", f"{LEFT}/image_rect_color"), ("visual_slam/camera_info_0", f"{LEFT}/camera_info"),
                      ("visual_slam/image_1", f"{RIGHT}/image_rect_color"), ("visual_slam/camera_info_1", f"{RIGHT}/camera_info"),
                      ("visual_slam/tracking/odometry", "perception/odom")]
            if imu:
                remaps.append(("visual_slam/imu", "zed/zed_node/imu/data"))
            composables.append(ComposableNode(
                package="isaac_ros_visual_slam", plugin="nvidia::isaac_ros::visual_slam::VisualSlamNode",
                name="visual_slam_node", namespace=ns, parameters=[vslam], remappings=remaps))
        if want_depth:
            composables.append(ComposableNode(
                package="isaac_ros_stereo_image_proc", plugin="nvidia::isaac_ros::stereo_image_proc::DisparityNode",
                name="disparity", namespace=ns,
                parameters=[{"use_sim_time": sim_time, "backend": "CUDA",
                             "max_disparity": float(LaunchConfiguration("max_disparity").perform(context)),
                             "confidence_threshold": int(LaunchConfiguration("confidence").perform(context))}],
                remappings=[("left/image_rect", f"{LEFT}/image_rect_color"), ("left/camera_info", f"{LEFT}/camera_info"),
                            ("right/image_rect", f"{RIGHT}/image_rect_color"), ("right/camera_info", f"{RIGHT}/camera_info"),
                            ("disparity", "perception/disparity")]))
    elif backend == "ros2":
        if want_odom:
            actions.append(Node(
                package="rtabmap_odom", executable="stereo_odometry", name="stereo_odometry", namespace=ns, output="screen",
                parameters=[{"use_sim_time": sim_time, "frame_id": frames["base"], "odom_frame_id": "odom",
                             "publish_tf": False, "approx_sync": True, "approx_sync_max_interval": 0.02,
                             "wait_for_transform": 0.5, "qos": 2, "qos_camera_info": 2,
                             "Odom/Strategy": "0", "Vis/MinInliers": "12", "Vis/CorType": "0",
                             "OdomF2M/MaxSize": "1000", "Odom/ResetCountdown": "0"}],
                remappings=[("left/image_rect", f"{LEFT}/image_rect_color"), ("left/camera_info", f"{LEFT}/camera_info"),
                            ("right/image_rect", f"{RIGHT}/image_rect_color"), ("right/camera_info", f"{RIGHT}/camera_info"),
                            ("odom", "perception/odom")]))
        if want_depth:
            composables.append(ComposableNode(
                package="stereo_image_proc", plugin="stereo_image_proc::DisparityNode", name="disparity", namespace=ns,
                parameters=[{"use_sim_time": sim_time, "approximate_sync": True, "stereo_algorithm": 1,   # 1 = SGBM
                             "disparity_range": 64, "correlation_window_size": 7, "min_disparity": 0,
                             "uniqueness_ratio": 10.0, "speckle_size": 100, "speckle_range": 4}],
                remappings=[("left/image_rect", f"{LEFT}/image_rect_color"), ("left/camera_info", f"{LEFT}/camera_info"),
                            ("right/image_rect", f"{RIGHT}/image_rect_color"), ("right/camera_info", f"{RIGHT}/camera_info"),
                            ("disparity", "perception/disparity")]))
        container = "component_container_mt"
    else:
        raise RuntimeError(f"unknown backend {backend!r} (isaac_ros | ros2)")

    if composables:
        actions.append(ComposableNodeContainer(
            name="perception_container", namespace=ns, package="rclcpp_components", executable=container,
            composable_node_descriptions=composables, output="screen"))
    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("backend", default_value="isaac_ros"),
        DeclareLaunchArgument("drone_id", default_value="1"),
        DeclareLaunchArgument("feed_mavros", default_value="true"),
        DeclareLaunchArgument("odom", default_value="true"),
        DeclareLaunchArgument("depth", default_value="true"),
        DeclareLaunchArgument("imu", default_value="false"),
        DeclareLaunchArgument("use_sim_time", default_value="true"),
        DeclareLaunchArgument("confidence", default_value="60000"),     # isaac_ros disparity confidence threshold (0-65535)
        DeclareLaunchArgument("max_disparity", default_value="64.0"),   # isaac_ros disparity search range, px
        OpaqueFunction(function=_nodes),
    ])
