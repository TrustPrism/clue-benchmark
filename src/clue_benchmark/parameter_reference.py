"""Authored parameter semantics with independently enforced field coverage."""

import json
from dataclasses import fields
from importlib.resources import files

from .community_config import CommunityConfig
from .config import Config


def parameter_paths():
    paths = {"schema_version"}
    config = CommunityConfig()
    for section in ("puzzle", "evidence", "distribution", "presentation", "dataset"):
        for field in fields(getattr(config, section)):
            if section == "puzzle" and field.name == "config":
                paths.update("puzzle.config." + f.name for f in fields(Config))
            else:
                paths.add(section + "." + field.name)
    return paths


def explain_config(config):
    reference = json.loads(
        files("clue_benchmark").joinpath("resources", "parameters.json").read_text()
    )
    if set(reference) != parameter_paths():
        raise ValueError("parameter reference coverage differs from dataclasses")
    resolved = config.to_dict()
    result = {}
    for path, description in reference.items():
        value = resolved
        for key in path.split("."):
            value = value[key]
        result[path] = {"value": value, "description": description}
    return result
