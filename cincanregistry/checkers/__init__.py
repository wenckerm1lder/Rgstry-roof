# import sys
# import inspect
# import pkgutil
# from pathlib import Path
# from importlib import import_module
from ._checker import UpstreamChecker, NO_VERSION
from .github import GitHubChecker
from .gitlab import GitLabChecker
from .bitbucket import BitbucketChecker
from .pypi import PypiChecker
from .debian import DebianChecker
from .alpine import AlpineChecker
from .didierstevens import DidierStevensChecker

classmap = {
    "github": GitHubChecker,
    "gitlab": GitLabChecker,
    "bitbucket": BitbucketChecker,
    "pypi": PypiChecker,
    "debian": DebianChecker,
    "alpine": AlpineChecker,
    "didierstevens@github": DidierStevensChecker,
}

__all__ = [
    "GitHubChecker",
    "GitLabChecker",
    "BitbucketChecker",
    "PypiChecker",
    "DebianChecker",
    "AlpineChecker",
    "DidierStevensChecker",
    "UpstreamChecker",
    "classmap",
    "NO_VERSION"
]

# for (_, name, _) in pkgutil.iter_modules([Path(__file__).parent]):
#     imported_module = import_module("." + name, package=__name__)
#     for i in dir(imported_module):
#         attribute = getattr(imported_module, i)
#         if inspect.isclass(attribute) and issubclass(attribute, UpstreamChecker):
#             setattr(sys.modules[__name__], name, attribute)
