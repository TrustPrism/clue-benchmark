"""Validated, serializable generation controls."""

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field

VERSION = "0.2.0"
DATA_VERSION = "0.2.0"
TYPES = (
    "unary_positive",
    "unary_negative",
    "crime_positive",
    "crime_negative",
    "crime_same_as",
    "crime_different_from",
    "indirect_positive",
    "indirect_negative",
)
DEFAULT_DOMAINS = {
    "weapon": ["Rope", "Wrench", "Poison", "Knife"],
    "location": ["Study", "Kitchen", "Library", "Garden"],
    "motive": ["Revenge", "Inheritance", "Jealousy", "Blackmail"],
    "time": ["20:00", "21:00", "22:00", "23:00"],
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class Config:
    suspect_count: int = 4
    domains: dict = field(
        default_factory=lambda: {k: list(v) for k, v in DEFAULT_DOMAINS.items()}
    )
    clue_count: int = 8
    enabled_types: tuple = TYPES
    alpha: float = 0.7
    beta: float = 0.75
    min_murderer_links: int = 1
    max_murderer_links: int | None = None
    max_positive_murderer_links: int | None = None
    min_indirect_clues: int = 0
    min_unique_subset_size: int = 1
    require_indirect_essential: bool = False
    max_attempts: int = 64
    mutation_steps: int = 12
    max_solver_calls: int = 10000
    solver_seconds: float = 2.0
    solver_work: float = 0.2
    generation_seconds: float = 30.0

    def __post_init__(self):
        if not isinstance(self.domains, dict) or any(
            not isinstance(v, (list, tuple)) for v in self.domains.values()
        ):
            raise ValueError("domains must map attribute names to value lists")
        if not isinstance(self.enabled_types, (list, tuple)):
            raise ValueError("enabled_types must be a list or tuple")
        object.__setattr__(self, "enabled_types", tuple(sorted(self.enabled_types)))
        object.__setattr__(
            self, "domains", {k: list(self.domains[k]) for k in sorted(self.domains)}
        )
        for key in (
            "suspect_count",
            "clue_count",
            "max_attempts",
            "max_solver_calls",
            "min_unique_subset_size",
        ):
            value = getattr(self, key)
            if type(value) is not int or value < 1:
                raise ValueError(f"{key} must be a positive integer")
        if not 2 <= self.suspect_count <= 64:
            raise ValueError("suspect_count must be 2..64")
        if not 1 <= len(self.domains) <= 8:
            raise ValueError("use 1..8 attributes")
        for attr, values in self.domains.items():
            if not isinstance(attr, str) or not attr.strip():
                raise ValueError("invalid attribute")
            if not 2 <= len(values) <= 32 or any(
                not isinstance(v, str) or not v.strip() for v in values
            ):
                raise ValueError("each domain needs 2..32 nonempty strings")
            if len(set(values)) != len(values):
                raise ValueError("duplicate domain value")
        if (
            not self.enabled_types
            or len(set(self.enabled_types)) != len(self.enabled_types)
            or set(self.enabled_types) - set(TYPES)
        ):
            raise ValueError("invalid enabled_types")
        for name in ("alpha", "beta"):
            if (
                not math.isfinite(getattr(self, name))
                or not 0 <= getattr(self, name) <= 1
            ):
                raise ValueError(name)
        for name in ("min_murderer_links", "min_indirect_clues", "mutation_steps"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 0:
                raise ValueError(name)
        for name in ("solver_seconds", "solver_work", "generation_seconds"):
            if not math.isfinite(getattr(self, name)) or getattr(self, name) <= 0:
                raise ValueError(name)
        for name in ("max_murderer_links", "max_positive_murderer_links"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(name)
        if (
            max(
                self.min_murderer_links,
                self.min_indirect_clues,
                self.min_unique_subset_size,
            )
            > self.clue_count
        ):
            raise ValueError("minimum exceeds clue count")
        if (
            self.max_murderer_links is not None
            and self.max_murderer_links < self.min_murderer_links
        ):
            raise ValueError("inconsistent link limits")
        if type(self.require_indirect_essential) is not bool:
            raise ValueError("require_indirect_essential")

    def to_dict(self):
        return json.loads(json.dumps(asdict(self)))

    @property
    def fingerprint(self):
        return digest({"version": DATA_VERSION, "config": self.to_dict()})


STUDY_PRESETS = {
    "easy": dict(
        alpha=0.95,
        beta=0.95,
        clue_count=5,
        min_unique_subset_size=3,
        max_murderer_links=2,
    ),
    "medium": dict(
        alpha=0.70,
        beta=0.75,
        clue_count=7,
        min_unique_subset_size=4,
        max_murderer_links=2,
        max_positive_murderer_links=1,
        min_indirect_clues=1,
        require_indirect_essential=True,
    ),
    "hard": dict(
        alpha=0.45,
        beta=0.55,
        clue_count=8,
        min_unique_subset_size=5,
        min_murderer_links=2,
        max_murderer_links=3,
        max_positive_murderer_links=1,
        min_indirect_clues=2,
        require_indirect_essential=True,
    ),
}
