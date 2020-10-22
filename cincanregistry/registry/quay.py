from typing import Dict
from ._registry import RemoteRegistry
from cincanregistry import ToolInfo


class QuayRegistry(RemoteRegistry):

    def __init__(self, *args, **kwargs):
        super(QuayRegistry, self).__init__(*args, **kwargs)

    def get_tools(self, defined_tag: str = "") -> Dict[str, ToolInfo]:
        pass

    def fetch_tags(self, tool: ToolInfo, update_cache: bool = False):
        pass
