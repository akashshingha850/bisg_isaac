"""zed_wrapper for drone N, with the contract's topic names. Used by BOTH the sim (docker/compose.yaml `zed`) and the
Jetson (deploy/jetson/compose.yaml `zed`), so the two cannot drift.

    ros2 launch /workspace/deploy/launch/zed_drone.launch.py drone_id:=1 params:=<params.yaml> [sim_mode:=true sim_port:=30000]

Why not just `zed_camera.launch.py namespace:=drone_1`: the stock launch then names the node after the camera and
publishes under `/drone_1/zed/...`, without the `zed_node` segment. docs/interface-contract.md fixes
`/drone_<n>/zed/zed_node/...`, which is what you get with the DEFAULT launch (`/zed/zed_node/...`) when the whole
thing is pushed into the `drone_<n>` namespace — exactly what this file does.

One catch: the stock launch loads its node into a container named `/zed/zed_container` (absolute, built without the
pushed namespace), while the container itself now lives at `/drone_<n>/zed/zed_container`, so the load call would wait
forever. The remap below points the container's load service at the name the launch is looking for. The loaded node
still lands in `/drone_<n>/zed/`.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import PushRosNamespace, SetRemap
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    declared = [
        DeclareLaunchArgument("drone_id", default_value="1", description="1-based drone number -> namespace drone_<n>"),
        DeclareLaunchArgument("camera_model", default_value="zedm"),
        DeclareLaunchArgument("params", default_value="", description="params override YAML (deploy/jetson/zed_params.yaml)"),
        DeclareLaunchArgument("sim_mode", default_value="false", description="true = read the Isaac Sim stream"),
        DeclareLaunchArgument("sim_address", default_value="127.0.0.1"),
        DeclareLaunchArgument("sim_port", default_value="30000"),
    ]
    zed = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([FindPackageShare("zed_wrapper"), "launch", "zed_camera.launch.py"])),
        launch_arguments={
            "camera_model": LaunchConfiguration("camera_model"),
            "ros_params_override_path": LaunchConfiguration("params"),
            "sim_mode": LaunchConfiguration("sim_mode"),
            "sim_address": LaunchConfiguration("sim_address"),
            "sim_port": LaunchConfiguration("sim_port"),
        }.items(),
    )
    ns = ["drone_", LaunchConfiguration("drone_id")]
    load_service = "/zed/zed_container/_container/load_node"
    return LaunchDescription(declared + [GroupAction([
        PushRosNamespace(ns),
        SetRemap(src=["/drone_", LaunchConfiguration("drone_id"), load_service], dst=load_service),
        zed,
    ])])
