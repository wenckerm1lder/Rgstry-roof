from typing import Dict, List
import json


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
        self.dict_form = manifest
        self.schemaVersion: int = manifest.get("schemaVersion", None)
        if self.schemaVersion != 2:
            raise TypeError(f"Unsupported Manifest schema version: {self.schemaVersion}")
        self.mediaType: str = manifest.get("mediaType", "")
        if self.mediaType.casefold() == self.MANIFEST_LIST_MIME.casefold():
            # Manifest list aka "fat manifest"
            # TODO implement rest as separate object
            self.manifests: List[Dict] = manifest.get("manifests", [])
        elif self.mediaType.casefold() == self.MANIFEST_IMAGE_MIME.casefold():
            # Image manifest
            self.config: ConfigReference = ConfigReference(manifest.get("config", {}))
            self.layers: List[LayerObject] = [LayerObject(layer) for layer in manifest.get("layers", [])]
            self.labels: Dict = {}

        else:
            raise TypeError(f"Unsupported Manifest MIME type: {self.mediaType}")

    def __str__(self):
        return json.dumps(self.dict_form, indent=2)


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


class LayerObject:
    """
    Layer object, based on the Manifest V2 schema
    
    General MIME: application/vnd.docker.image.rootfs.diff.tar.gz
    Might be: application/vnd.docker.image.rootfs.foreign.diff.tar.gzip on pull (never push)
    """

    def __init__(self, layer: Dict):
        self.mediaType: str = layer.get("mediaType")
        self.size: int = layer.get("size")
        self.digest: str = layer.get("digest")
        self.urls: List = layer.get("urls", [])
        if not (self.mediaType and self.size and self.digest):
            raise ValueError("MediaType, size and digest is required for layer.")


class ImageConfig:
    """
    Based on the config schema: https://github.com/opencontainers/image-spec/blob/master/config.md
    """

    def __init__(self, image_config: Dict):
        self.created: str = image_config.get("created", "")
        self.author: str = image_config.get("author", "")
        self.architecture: str = image_config.get("architecture")
        self.os: str = image_config.get("os")
        # Config used on container creation
        self.config: Dict = image_config.get("config", {})
        self.rootfs: Dict = image_config.get("rootfs")
        self.history: Dict = image_config.get("history", {})

        # some params not in OCI spec, added by Docker #
        self.container: str = image_config.get("container", "")
        # Config from the last layer of the build
        self.container_config: Dict = image_config.get("container_config", {})
        self.docker_version: str = image_config.get("docker_version", "")
        if not (self.architecture and self.os and self.rootfs):
            raise ValueError("Invalid container conf, missing required fields")
