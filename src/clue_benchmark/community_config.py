"""Versioned community-generation contracts, separate from frozen releases."""

import math
from dataclasses import asdict, dataclass, field

from .config import Config, digest

SCHEMA_VERSION = "clue-community-1"
FAMILIES = {
    "standard": None,
    "pairwise": {"crime_positive", "unary_positive", "suspect_different_from"},
    "cross_attribute": {"crime_positive", "unary_positive", "indirect_negative"},
    "equality_tree": {"crime_positive", "unary_positive", "suspect_same_as"},
    "branching": {"crime_positive", "unary_positive", "suspect_same_as"},
    "redundant_paths": {"crime_positive", "unary_positive", "suspect_same_as"},
}


def integer(value, name, lower=0, upper=None):
    if type(value) is not int or value < lower or (upper is not None and value > upper):
        raise ValueError(
            f"{name} must be an integer in {lower}..{upper or 'unbounded'}"
        )


@dataclass(frozen=True)
class PuzzleConfig:
    # Nested legacy configuration retains all historical controls unchanged.
    config: dict = field(default_factory=dict)
    family: str = "standard"
    assignment_mode: str = "repeated"
    extra_clue_scope: str = "all"
    attribute_mismatches: int | None = None

    def __post_init__(self):
        cfg = Config(**self.config)
        if self.family not in FAMILIES:
            raise ValueError("unsupported family")
        if self.attribute_mismatches is not None:
            integer(
                self.attribute_mismatches, "attribute_mismatches", 1, len(cfg.domains)
            )
            if self.family != "redundant_paths":
                raise ValueError("attribute_mismatches requires redundant_paths")
        if self.extra_clue_scope not in ("all", "non_target_attributes"):
            raise ValueError("unsupported extra clue scope")
        if self.extra_clue_scope == "non_target_attributes" and (
            self.family not in ("equality_tree", "branching") or len(cfg.domains) < 2
        ):
            raise ValueError(
                "non_target_attributes requires an equality family and two attributes"
            )
        if self.assignment_mode not in ("repeated", "distinct"):
            raise ValueError("unsupported assignment mode")
        if FAMILIES[self.family] and not FAMILIES[self.family] <= set(
            cfg.enabled_types
        ):
            raise ValueError("family requires disabled clue types")
        if self.family == "cross_attribute" and len(cfg.domains) < 2:
            raise ValueError("cross_attribute requires two attributes")
        if self.assignment_mode == "distinct":
            if any(len(v) < cfg.suspect_count for v in cfg.domains.values()):
                raise ValueError("distinct assignment requires enough values")
            if self.family in ("equality_tree", "branching", "redundant_paths"):
                raise ValueError("equality constructions require repeated values")
            if cfg.active_values_per_attribute is not None and (
                cfg.active_values_per_attribute < cfg.suspect_count
            ):
                raise ValueError("active values cannot satisfy distinct assignments")
        if self.family in ("equality_tree", "branching", "redundant_paths"):
            if cfg.reasoning_route != "standard":
                raise ValueError("constructed family conflicts with reasoning_route")
            if cfg.clue_count < cfg.suspect_count:
                raise ValueError("equality construction needs at least n clues")
            if self.family == "redundant_paths" and cfg.clue_count != (
                (cfg.suspect_count + 1) * len(cfg.domains)
            ):
                raise ValueError("redundant_paths requires n+1 reports per attribute")
        elif self.family != "standard" and cfg.reasoning_route not in (
            "standard",
            self.family,
        ):
            raise ValueError("family conflicts with reasoning_route")
        object.__setattr__(self, "config", cfg.to_dict())


@dataclass(frozen=True)
class EvidenceConfig:
    minimum_sufficient_clues: int | None = None
    maximum_sufficient_clues: int | None = None
    entailed_clues: int = 0
    connected_decoys: int = 0
    irrelevant_records: int = 0
    false_reports: int = 0
    corruption_allowance: int | None = None
    answerability: str = "unique"
    corruption_strategy: str = "random"
    corruption_search_attempts: int = 12
    maximum_alternative_margin: int | None = None

    def __post_init__(self):
        for name in (
            "entailed_clues",
            "connected_decoys",
            "irrelevant_records",
            "false_reports",
        ):
            integer(getattr(self, name), name)
        if self.corruption_strategy not in ("random", "targeted"):
            raise ValueError("unsupported corruption strategy")
        if (
            self.corruption_strategy == "targeted"
            and self.false_reports
            and self.answerability != "unique"
        ):
            raise ValueError("targeted corruption supports unique cases only")
        integer(self.corruption_search_attempts, "corruption_search_attempts", 1)
        if self.maximum_alternative_margin is not None:
            integer(self.maximum_alternative_margin, "maximum_alternative_margin", 1)
            if self.answerability != "unique":
                raise ValueError("alternative margin requires a unique answer")
        integer(self.false_reports, "false_reports", upper=2)
        allowance = (
            self.false_reports
            if self.corruption_allowance is None
            else self.corruption_allowance
        )
        integer(allowance, "corruption_allowance", upper=2)
        if allowance < self.false_reports:
            raise ValueError("corruption allowance excludes sampled world")
        object.__setattr__(self, "corruption_allowance", allowance)
        for name in ("minimum_sufficient_clues", "maximum_sufficient_clues"):
            if getattr(self, name) is not None:
                integer(getattr(self, name), name)
        if (
            self.minimum_sufficient_clues is not None
            and self.maximum_sufficient_clues is not None
            and self.minimum_sufficient_clues > self.maximum_sufficient_clues
        ):
            raise ValueError("inconsistent sufficient-clue bounds")
        if self.answerability not in ("unique", "ambiguous"):
            raise ValueError("answerability must be unique or ambiguous")
        if self.answerability == "ambiguous" and any(
            v is not None
            for v in (self.minimum_sufficient_clues, self.maximum_sufficient_clues)
        ):
            raise ValueError("ambiguous banks have no sufficient subset")


@dataclass(frozen=True)
class DistributionConfig:
    agent_count: int = 2
    shared_reports: int = 0
    private_replication: int = 1
    per_agent_quotas: list[int] | None = None
    minimum_coalition_size: int | None = 2
    max_attempts: int = 128

    def __post_init__(self):
        integer(self.agent_count, "agent_count", 1, 8)
        integer(self.shared_reports, "shared_reports")
        integer(
            self.private_replication,
            "private_replication",
            1,
            max(1, self.agent_count - 1),
        )
        integer(self.max_attempts, "partition max_attempts", 1)
        if self.minimum_coalition_size is not None:
            integer(
                self.minimum_coalition_size,
                "minimum_coalition_size",
                1,
                self.agent_count,
            )
        if self.per_agent_quotas is not None:
            if len(self.per_agent_quotas) != self.agent_count:
                raise ValueError("one quota per agent required")
            for v in self.per_agent_quotas:
                integer(v, "agent quota")


@dataclass(frozen=True)
class PresentationConfig:
    theme: str = "mystery"
    naming_seed: int = 0
    template: str = "compact"
    clue_order: str = "shuffle"
    evidence_placement: str = "front"
    minimum_words: int | None = None
    maximum_words: int | None = None
    minimum_tokens: int | None = None
    maximum_tokens: int | None = None

    def __post_init__(self):
        if self.theme not in ("mystery", "investigation"):
            raise ValueError("unsupported theme")
        if self.template not in ("compact", "expanded"):
            raise ValueError("unsupported deterministic template")
        if self.clue_order not in ("shuffle", "canonical", "reverse"):
            raise ValueError("unsupported clue order")
        if self.evidence_placement not in ("front", "middle", "end", "interleaved"):
            raise ValueError("unsupported evidence placement")
        integer(self.naming_seed, "naming_seed")
        for name in (
            "minimum_words",
            "maximum_words",
            "minimum_tokens",
            "maximum_tokens",
        ):
            if getattr(self, name) is not None:
                integer(getattr(self, name), name)
        for unit in ("words", "tokens"):
            lo, hi = getattr(self, "minimum_" + unit), getattr(self, "maximum_" + unit)
            if lo is not None and hi is not None and lo > hi:
                raise ValueError(f"inconsistent {unit} bounds")


@dataclass(frozen=True)
class DatasetConfig:
    count: int = 1
    seed: int = 0
    workers: int = 1
    splits: dict = field(default_factory=lambda: {"development": 0.8, "test": 0.2})
    holdout_families: list[str] = field(default_factory=list)
    output_directory: str = "community-output"
    certification_seconds: float = 60
    max_solver_calls: int = 20000
    max_candidates_per_case: int = 20
    large_corpus: bool = False

    def __post_init__(self):
        for name in ("count", "workers", "max_solver_calls", "max_candidates_per_case"):
            integer(getattr(self, name), name, 1)
        integer(self.seed, "seed")
        if type(self.large_corpus) is not bool:
            raise ValueError("large_corpus must be boolean")
        if (
            not math.isfinite(self.certification_seconds)
            or self.certification_seconds <= 0
        ):
            raise ValueError("certification_seconds must be positive")
        if not isinstance(self.output_directory, str) or not self.output_directory:
            raise ValueError("output_directory required")
        if (
            not self.splits
            or set(self.splits) - {"development", "test", "transfer"}
            or any(
                type(v) not in (int, float) or not math.isfinite(v) or v < 0
                for v in self.splits.values()
            )
            or not math.isclose(sum(self.splits.values()), 1)
        ):
            raise ValueError("splits must be nonnegative proportions summing to one")
        if set(self.holdout_families) - set(FAMILIES):
            raise ValueError("unsupported holdout family")


@dataclass(frozen=True)
class CommunityConfig:
    puzzle: PuzzleConfig = field(default_factory=PuzzleConfig)
    evidence: EvidenceConfig = field(default_factory=EvidenceConfig)
    distribution: DistributionConfig = field(default_factory=DistributionConfig)
    presentation: PresentationConfig = field(default_factory=PresentationConfig)
    dataset: DatasetConfig = field(default_factory=DatasetConfig)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self):
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported community schema version")
        if (
            self.evidence.minimum_sufficient_clues is not None
            and self.evidence.minimum_sufficient_clues
            < self.puzzle.config["min_unique_subset_size"]
        ):
            raise ValueError("minimum sufficient clues conflicts with legacy minimum")
        if (
            self.evidence.answerability == "ambiguous"
            and self.distribution.minimum_coalition_size is not None
        ):
            raise ValueError("ambiguous mode requires minimum_coalition_size=null")
        if self.distribution.shared_reports > (
            self.puzzle.config["clue_count"]
            + self.evidence.entailed_clues
            + self.evidence.connected_decoys
            + self.evidence.irrelevant_records
        ):
            raise ValueError("shared reports exceed total reports")
        if not self.dataset.large_corpus and self.evidence.irrelevant_records > 1000:
            raise ValueError("more than 1000 nuisance records requires large_corpus")

    @classmethod
    def from_dict(cls, value):
        value = dict(value)
        constructors = {
            "puzzle": PuzzleConfig,
            "evidence": EvidenceConfig,
            "distribution": DistributionConfig,
            "presentation": PresentationConfig,
            "dataset": DatasetConfig,
        }
        for name, constructor in constructors.items():
            if name in value:
                value[name] = constructor(**value[name])
        return cls(**value)

    def to_dict(self):
        return asdict(self)

    @property
    def fingerprint(self):
        value = self.to_dict()
        # Execution location/parallelism does not change dataset identities.
        value["dataset"].pop("workers")
        value["dataset"].pop("output_directory")
        return digest(value)
