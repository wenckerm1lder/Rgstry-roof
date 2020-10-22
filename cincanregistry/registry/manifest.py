from typing import Dict, List


class ManifestV2:
    """
    Manifest object, based on the schema described in
    here https://docs.docker.com/registry/spec/manifest-v2-2/

    Raises TypeError if invalid schema
    """
    MANIFEST_LIST_MIME = "application/vnd.docker.distribution.manifest.list.v2+json"
    MANIFEST_IMAGE_MIME = "application/vnd.docker.distribution.manifest.v2+json"

    def __init__(self, manifest: Dict):
        """
        Image manifest or Manifest list
        """
        self.schemaVersion: int = manifest.get("schemaVersion", None)
        if self.schemaVersion != 2:
            raise TypeError(f"Unsupported Manifest schema version: {self.schemaVersion}")
        self.mediaType: str = manifest.get("mediaType", "")
        if self.mediaType.casefold() == self.MANIFEST_LIST_MIME.casefold():
            # Manifest list aka "fat manifest"
            # TODO implement rest
            self.manifests: List[Dict] = manifest.get("manifests", [])
        elif self.mediaType.casefold() == self.MANIFEST_IMAGE_MIME.casefold():
            # Image manifest
            self.config: ConfigReference = ConfigReference(manifest.get("config", {}))
            self.layers: List[Dict] = manifest.get("layers", [])
            self.labels: Dict = {}

        else:
            raise TypeError(f"Unsupported Manifest MIME type: {self.mediaType}")


class ConfigReference:
    """
    Reference object to container configuration object based on Manifest V2 schema
    """
    CONTAINER_CONFIG_MIME = "application/vnd.docker.container.image.v1+json"

    def __init__(self, config: Dict):
        self.mediaType: str = config.get("mediaType", "")
        if self.mediaType.casefold() != self.CONTAINER_CONFIG_MIME.casefold():
            raise TypeError(f"Invalid type for container config: {self.mediaType}")
        self.size: int = config.get("size", None)
        self.digest: str = config.get("digest", "")
        if not self.digest or not self.digest.startswith("sha256:"):
            raise ValueError("Reference digest for configuration object cannot be null or invalid format.")
