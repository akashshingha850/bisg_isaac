from glob import glob

from setuptools import find_packages, setup

package_name = "bisg_perception"

setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.py")),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="bisg_isaac",
    maintainer_email="akashshingha850@gmail.com",
    description="Perception backends (isaac_ros | ros2) and benchmark",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "tf_relay = bisg_perception.tf_relay:main",
            "bench = bisg_perception.bench:main",
        ],
    },
)
