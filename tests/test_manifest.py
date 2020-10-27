import pytest
from cincanregistry.registry.manifest import LayerObject

LAYER_OBJ = {
    "mediaType": "testMedia",
    "size": "testSize",
    "digest": "testDigest"
}


def test_layer_object():
    try:
        testLayer = LayerObject(LAYER_OBJ)
    except ValueError:
        pytest.fail("Unexpected exception.")

    assert testLayer.mediaType == "testMedia"
    assert testLayer.size == "testSize"
    assert testLayer.digest == "testDigest"
    LAYER_OBJ["size"] = ""

    with pytest.raises(ValueError) as e:
        testLayer = LayerObject(LAYER_OBJ)


