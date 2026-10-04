from setuptools import find_packages, setup

package_name = "bisg_vehicle"

setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="bisg_isaac",
    maintainer_email="akashshingha850@gmail.com",
    description="Per-drone vehicle nodes: vio_mock (sim), vio_relay (real)",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "vio_mock = bisg_vehicle.vio_mock:main",
        ],
    },
)
