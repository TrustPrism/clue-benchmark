"""Configurable, certified clue datasets and original puzzle generation."""

from .community_bundle import (
    generate_dataset,
    iter_cases,
    profile_dataset,
    validate_dataset,
)
from .community_config import CommunityConfig
from .community_generation import generate_case, partition, score
from .config import VERSION as __version__
from .config import Config
from .generation import generate, validate_case
from .presets import resolve_config
from .public_api import evaluate_agent, export_public, inspect_case

__all__ = [
    "__version__",
    "evaluate_agent",
    "export_public",
    "inspect_case",
    "resolve_config",
    "CommunityConfig",
    "generate_case",
    "generate_dataset",
    "iter_cases",
    "partition",
    "profile_dataset",
    "score",
    "validate_dataset",
    "Config",
    "generate",
    "validate_case",
]
