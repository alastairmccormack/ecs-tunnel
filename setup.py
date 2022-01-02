from setuptools import setup, find_packages

version = '0.1.0'

setup(
    name='ecs-tunnel',
    version=version,
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click',
        'boto3',
        'pexpect',
        'jmespath',
    ],
    entry_points={
        'console_scripts': [
            'ecs-tunnel = ecs_tunnel.cli:cli',
        ],
    },
    python_requires='>=3.8',
)
