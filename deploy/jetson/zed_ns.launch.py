"""ZED Mini wrapper under /drone_<DRONE_ID> (docs/interface-contract.md: zed/zed_node/*).

The wrapper's own `namespace` arg replaces the node name with the camera name (topics would become
/drone_1/zed/* and frames would change), so push the drone namespace around the stock launch instead. The stock launch loads zed_node into
the hard-coded absolute container '/zed/<container_name>', which a pushed namespace never reaches, so
the container is created here at exactly that name; zed_node itself still resolves under the push.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import GroupAction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import ComposableNodeContainer, PushROSNamespace


def generate_launch_description():
    zed_launch = os.path.join(get_package_share_directory('zed_wrapper'), 'launch', 'zed_camera.launch.py')
    return LaunchDescription([GroupAction([
        PushROSNamespace('drone_' + os.environ.get('DRONE_ID', '1')),
        ComposableNodeContainer(name='zed_container', namespace='/zed', package='rclcpp_components',
                                executable='component_container_isolated', output='screen',
                                arguments=['--use_multi_threaded_executor', '--ros-args', '--log-level', 'info'],
                                composable_node_descriptions=[]),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(zed_launch), launch_arguments={
            'camera_model': 'zedm',
            'container_name': 'zed_container',
            'ros_params_override_path': '/workspace/deploy/jetson/zed_params.yaml',
        }.items()),
    ])])
