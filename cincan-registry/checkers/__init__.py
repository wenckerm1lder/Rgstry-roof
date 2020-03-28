# import sys
# import inspect
# import pkgutil
# from pathlib import Path
# from importlib import import_module
# from ._checker import UpstreamChecker
from .github import GitHubChecker

classmap = {
    "github": GitHubChecker,
}

__all__ = ["GitHubChecker"]

# for (_, name, _) in pkgutil.iter_modules([Path(__file__).parent]):
#     imported_module = import_module("." + name, package=__name__)
#     for i in dir(imported_module):
#         attribute = getattr(imported_module, i)
#         if inspect.isclass(attribute) and issubclass(attribute, UpstreamChecker):
#             setattr(sys.modules[__name__], name, attribute)
