# mypy: allow-untyped-defs

from configparser import ConfigParser
import os
import sys
from collections import OrderedDict
from typing import Dict, Mapping, Optional, List

here = os.path.dirname(__file__)


class ConfigDict(Dict[str, str]):
    def __init__(self, base_path: str, *args: str, **kwargs: str):
        self.base_path = base_path
        dict.__init__(self, *args, **kwargs)

    def _normalize_path(self, path: str) -> str:
        os.path.expanduser(path)
        return os.path.abspath(os.path.join(self.base_path, path))

    def get_path(self, key: str, default:Optional[str] = None) -> Optional[str]:
        if key not in self:
            return default
        return self._normalize_path(self[key])

    def get_paths(self, key: str, default:Optional[List[str]] = None) -> Optional[List[str]]:
        if key not in self:
            return default
        return [self._normalize_path(item.strip()) for item in self[key].split(";")]


def read(config_path: str) -> Mapping[str, ConfigDict]:
    config_path = os.path.abspath(config_path)
    config_root = os.path.dirname(config_path)
    parser = ConfigParser()
    success = parser.read(config_path)
    assert config_path in success, success

    subns = {"pwd": os.path.abspath(os.path.curdir)}

    rv = OrderedDict()
    for section in parser.sections():
        rv[section] = ConfigDict(config_root)
        for key in parser.options(section):
            rv[section][key] = parser.get(section, key, raw=False, vars=subns)

    return rv


def path(argv=None):
    if argv is None:
        argv = []
    path = None

    for i, arg in enumerate(argv):
        if arg == "--config":
            if i + 1 < len(argv):
                path = argv[i + 1]
        elif arg.startswith("--config="):
            path = arg.split("=", 1)[1]
        if path is not None:
            break

    if path is None:
        if os.path.exists("wptrunner.ini"):
            path = os.path.abspath("wptrunner.ini")
        else:
            path = os.path.join(here, "..", "wptrunner.default.ini")

    return os.path.abspath(path)


def load():
    return read(path(sys.argv))
