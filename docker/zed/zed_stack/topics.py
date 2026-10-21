"""What each ZED SDK module publishes (wrapper 5.4.1 names, under /drone_<n>/zed/zed_node/) and which switch advertises it."""

# module -> [(topic, block key that must be true, or None = always when the module is on)]
TOPICS = {
    "video": [("left/color/rect/image", "publish_left_right"), ("left/color/rect/camera_info", "publish_left_right"),
              ("right/color/rect/image", "publish_left_right"), ("right/color/rect/camera_info", "publish_left_right"),
              ("rgb/color/rect/image", "publish_rgb"), ("left/color/raw/image", "publish_raw"),
              ("left/gray/rect/image", "publish_gray"), ("stereo/color/rect/image", "publish_stereo")],
    "sensors": [("imu/data", "publish_imu"), ("imu/data_raw", "publish_imu_raw"),
                ("left_cam_imu_transform", "publish_cam_imu_transf")],
    "depth": [("depth/depth_registered", "publish_depth_map"), ("point_cloud/cloud_registered", "publish_point_cloud"),
              ("disparity/disparity_image", "publish_disparity"), ("confidence/confidence_map", "publish_depth_confidence"),
              ("depth/depth_info", "publish_depth_info")],
    "region_of_interest": [("roi_mask/image", "publish_roi_mask")],
    "positional_tracking": [("odom", "publish_odom_pose"), ("pose", "publish_odom_pose"), ("pose/status", None),
                            ("pose_with_covariance", "publish_pose_cov"), ("path_odom", "publish_cam_path"),
                            ("path_map", "publish_cam_path"), ("pose/landmarks", "publish_3d_landmarks")],
    "global_localization": [("geo_pose", None), ("pose/filtered", None), ("pose/fused_fix", None)],
    "spatial_mapping": [("mapping/fused_cloud", None)],
    "plane_detection": [("plane", None), ("plane_marker", None)],
    "object_detection": [("obj_det/objects", None)],
    "body_tracking": [("body_trk/skeletons", None)],
    "streaming": [],
    "recording": [],
}
ALWAYS = [("status/health", "Camera"), ("status/heartbeat", "Camera")]

# bridge module -> (what it consumes, what it produces)
BRIDGE = {
    "health": ("zed status/health, pose/status, image + depth liveness", "zed_stack/status (JSON), mavros/statustext/send"),
    "odometry": ("zed odom, pose/status", "mavros/odometry/out"),
    "obstacle_distance": ("zed depth_registered, left camera_info", "mavros/obstacle/send"),
}


def module_topics(cfg, name):
    blk = cfg.module(name)
    return [t for t, key in TOPICS.get(name, []) if key is None or blk.get(key, False)]
