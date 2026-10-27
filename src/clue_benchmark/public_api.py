"""Installed-wheel public observations and offline callable evaluation."""

import os
import tempfile
from copy import deepcopy
from pathlib import Path

from .community_bundle import iter_cases, load_evaluator_cases
from .community_generation import score
from .config import VERSION, canonical
from .dataset import atomic_json

# Positive allowlists prevent new evaluator fields from leaking through exports.
CASE_FIELDS = frozenset(
    {
        "kind",
        "case_id",
        "world_id",
        "presentation_id",
        "split",
        "suspects",
        "domains",
        "display_names",
        "assignment_mode",
        "agent_count",
        "corruption_allowance",
        "padding",
        "rules",
        "total_reports",
    }
)
REPORT_FIELDS = frozenset({"kind", "case_id", "report_id", "constraint", "text"})
CONSTRAINT_FIELDS = frozenset(
    {
        "type",
        "suspect",
        "other_suspect",
        "attribute",
        "value",
        "attr1",
        "attr2",
        "val1",
        "val2",
        "component",
        "variable",
        "domain",
    }
)


def public_records(dataset, agent_id=None):
    for row in iter_cases(dataset, agent_id):
        fields = CASE_FIELDS if row["kind"] == "case" else REPORT_FIELDS
        clean = {k: deepcopy(v) for k, v in row.items() if k in fields}
        if "constraint" in clean:
            clean["constraint"] = {
                k: v for k, v in clean["constraint"].items() if k in CONSTRAINT_FIELDS
            }
        yield clean


def export_public(dataset, output, agent_id=0):
    """Export evidence only. Refuse to overwrite any existing destination."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=output.parent, delete=False, encoding="utf-8"
        ) as stream:
            temporary = Path(stream.name)
            for row in public_records(dataset, agent_id):
                stream.write(canonical(row) + "\n")
                count += 1
            stream.flush()
            os.fsync(stream.fileno())
        # Atomic no-clobber publication, even if another exporter races us.
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {
        "software_version": VERSION,
        "output": str(output),
        "records": count,
        "agent_id": agent_id,
        "external_inference": False,
    }


def inspect_case(dataset, case_id=None, agent_id=0):
    """Public case only, never answers or certificates."""
    header, reports = None, []
    for row in public_records(dataset, agent_id):
        if row["kind"] == "case":
            if header is not None:
                break
            if case_id is None or row["case_id"] == case_id:
                header = row
        elif header is not None:
            reports.append(row)
    if header is None:
        raise ValueError("case_id not found")
    return {**header, "reports": reports}


def evaluate_agent(dataset, agent, output=None, agent_id=None):
    """Evaluate a trusted callable on public fields. This is not process isolation.

    The evaluator alone loads answers. For untrusted code, use a separate process
    with only an export_public file mounted, then score its responses offline.
    """
    if output is not None and Path(output).exists():
        raise ValueError("output exists; choose a new evaluator output path")
    cases = {c["case_id"]: c for c in load_evaluator_cases(dataset)}
    episodes, current, reports = [], None, []

    def finish():
        response = agent(deepcopy({**current, "reports": reports}))
        case = cases[current["case_id"]]
        episodes.append(
            {
                "case_id": current["case_id"],
                "world_id": current["world_id"],
                "response": response,
                **score(case, response, reports),
            }
        )

    for record in public_records(dataset, agent_id):
        if record["kind"] == "case":
            if current is not None:
                finish()
            current, reports = record, []
        else:
            reports.append(record)
    if current is not None:
        finish()
    result = {
        "software_version": VERSION,
        "status": "offline_external_agent",
        "agent_id": agent_id,
        "episodes": episodes,
        "external_inference": False,
    }
    if output is not None:
        if Path(output).exists():
            raise ValueError("output exists; choose a new evaluator output path")
        atomic_json(output, result, overwrite=False)
    return result
