from .registry import ToolRegistry


class DockerHubRegistry(ToolRegistry):
    """
    Inherits ToolRegistry class to get implementation of
    Docker Registry HTTP V2 API: https://docs.docker.com/registry/spec/api/
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registry_name = "Docker Hub"
        self.registry_root = "https://index.docker.io"
        self._set_auth_and_service_location()
