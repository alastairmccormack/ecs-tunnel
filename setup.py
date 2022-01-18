from setuptools import setup, find_packages

version = '0.2.0'

with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name='ecs-tunnel',
    author="Alastair McCormack",
    author_email="alastair@alumedia.co.uk",
    description="Tunnel ports via AWS ECS Tasks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/alastairmccormack/ecs-tunnel",
    project_urls={
        "Bug Tracker": "https://github.com/alastairmccormack/ecs-tunnel/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Utilities",
        "Topic :: System :: Systems Administration",
        "Topic :: System :: Networking"
    ],
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
