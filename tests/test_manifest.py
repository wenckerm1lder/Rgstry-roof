import pytest
from cincanregistry.models.manifest import LayerObject, ManifestV2, ConfigReference

EXAMPLE_MANIFEST = {
    "schemaVersion": 2,
    "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
    "config": {
        "mediaType": "application/vnd.docker.container.image.v1+json",
        "size": 5802,
        "digest": "sha256:7cc538b3587d8bbc0ad3fb0cbb2cdae9f7f562f26066f847a1b69964fcb71108"
    },
    "layers": [
        {
            "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
            "size": 2797541,
            "digest": "sha256:df20fa9351a15782c64e6dddb2d4a6f50bf6d3688060a34c4014b0d9a752eb4c"
        },
        {
            "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
            "size": 571030,
            "digest": "sha256:1845a58b389d04b11df55e5821a43f643acbab0ee1655351def7fd417ed1dcdd"
        },
        {
            "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
            "size": 23514464,
            "digest": "sha256:4c99df4b3f9e1dc36fcf7b4174e38859553aa0e0b0c3a18b254e7e2cf2758de0"
        },
        {
            "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
            "size": 17376017,
            "digest": "sha256:aafcfd7a6cc2a8b9c3ed6e00c5cdef865419e67b0320d3d516cd6de1067c06f8"
        },
        {
            "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
            "size": 884,
            "digest": "sha256:5ed32f2df971d5aac6e6ab7c587ae17f671a59a10f21d57cc16aa2885a5f6d67"
        },
        {
            "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
            "size": 460,
            "digest": "sha256:14ea8904eca8b82a0e17d821abc8501ca24f910115b32df355208a53f66a8b73"
        },
        {
            "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
            "size": 345,
            "digest": "sha256:d2ec885bb019b6fefdcf42e21cc68182ed32756a247d6deb5552473dab1b43ac"
        }
    ]
}

LAYER_OBJ = {
    "mediaType": "testMedia",
    "size": 1000,
    "digest": "testDigest",
    "urls": []
}


def test_layer_object():
    try:
        testLayer = LayerObject(LAYER_OBJ)
    except ValueError:
        pytest.fail("Unexpected exception.")

    assert testLayer.mediaType == "testMedia"
    assert testLayer.size == 1000
    assert testLayer.digest == "testDigest"
    LAYER_OBJ["size"] = ""

    with pytest.raises(ValueError) as e:
        LayerObject(LAYER_OBJ)

    LAYER_OBJ["urls"] = ["some-almost-valid-url.com"]
    LAYER_OBJ["size"] = 50
    testLayer = LayerObject(LAYER_OBJ)
    assert testLayer.size == 50
    assert testLayer.urls == ["some-almost-valid-url.com"]


def test_manifest_object_v2():
    manifest = ManifestV2(EXAMPLE_MANIFEST)
    assert manifest.schemaVersion == 2
    assert manifest.mediaType == "application/vnd.docker.distribution.manifest.v2+json"
    assert manifest.config.mediaType == "application/vnd.docker.container.image.v1+json"
    assert manifest.config.size == 5802
    assert manifest.config.digest == "sha256:7cc538b3587d8bbc0ad3fb0cbb2cdae9f7f562f26066f847a1b69964fcb71108"
    assert isinstance(manifest.layers[0], LayerObject)
    assert manifest.layers[0].digest == "sha256:df20fa9351a15782c64e6dddb2d4a6f50bf6d3688060a34c4014b0d9a752eb4c"

    with pytest.raises(TypeError):
        EXAMPLE_MANIFEST["schemaVersion"] = 1
        ManifestV2(EXAMPLE_MANIFEST)
    with pytest.raises(TypeError):
        EXAMPLE_MANIFEST["schemaVersion"] = 2
        EXAMPLE_MANIFEST["mediaType"] = "NotCorrect"
        ManifestV2(EXAMPLE_MANIFEST)


def test_config_reference():

    conf_ref = ConfigReference(EXAMPLE_MANIFEST.get("config"))
    assert conf_ref.size == 5802
    assert conf_ref.mediaType == "application/vnd.docker.container.image.v1+json"
    assert conf_ref.digest == "sha256:7cc538b3587d8bbc0ad3fb0cbb2cdae9f7f562f26066f847a1b69964fcb71108"

    EXAMPLE_MANIFEST["config"]["mediaType"] = "unsupported"
    with pytest.raises(TypeError):
        ConfigReference(EXAMPLE_MANIFEST.get("config"))
    EXAMPLE_MANIFEST["config"]["mediaType"] = "application/vnd.docker.container.image.v1+json"
    EXAMPLE_MANIFEST["config"]["digest"] = "not-starting-with-sha256"
    with pytest.raises(ValueError):
        ConfigReference(EXAMPLE_MANIFEST.get("config"))
