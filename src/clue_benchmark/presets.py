"""Small named configurations available from an installed wheel."""

import json
from importlib.resources import files

from .community_config import CommunityConfig

NAMES = (
    "quickstart",
    "distributed",
    "ambiguous",
    "false-reports",
    "noise-volume",
    "hard-example",
)


def preset(name):
    if name not in NAMES:
        raise ValueError(f"unknown preset {name!r}; choose from {', '.join(NAMES)}")
    return json.loads(
        files("clue_benchmark").joinpath("resources", name + ".json").read_text()
    )


def resolve_config(*, name=None, path=None, output=None, workers=None):
    if (name is None) == (path is None):
        raise ValueError("choose exactly one of --preset or --config")
    value = (
        preset(name)["config"]
        if name
        else json.loads(__import__("pathlib").Path(path).read_text())
    )
    if output is not None:
        value.setdefault("dataset", {})["output_directory"] = output
    if workers is not None:
        value.setdefault("dataset", {})["workers"] = workers
    return CommunityConfig.from_dict(value)
