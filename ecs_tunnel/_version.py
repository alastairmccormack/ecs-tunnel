import importlib.metadata

try:
    VERSION = importlib.metadata.version('ecs-tunnel')
except importlib.metadata.PackageNotFoundError:
    VERSION = 'develop'
