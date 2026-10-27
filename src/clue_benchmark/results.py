"""Recompute historical counts from indexed, sanitized assignment records."""

import hashlib
import json
from collections import defaultdict
from importlib.resources import files
from pathlib import Path

from .config import VERSION
from .dataset import atomic_json


def replay_results(output, figures=False):
    from .replay import write_report

    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    resources = files("clue_benchmark").joinpath("resources", "measured-results")
    index = json.loads(resources.joinpath("index.json").read_text())
    studies = {}
    for name, provenance in index.items():
        raw = resources.joinpath(name + ".json").read_bytes()
        if hashlib.sha256(raw).hexdigest() != provenance["sanitized_sha256"]:
            raise ValueError("sanitized replay hash mismatch: " + name)
        records = json.loads(raw)["episodes"]
        groups = defaultdict(list)
        for r in records:
            key = (
                r.get(
                    "arm",
                    r.get(
                        "original_job",
                        "fresh-hard"
                        if name == "flash-hard-scale"
                        else r.get("job", "all"),
                    ),
                ),
                r["model"],
                r["condition"],
            )
            groups[key].append(r)
        panels = []
        for (arm, model, condition), rows in sorted(groups.items()):
            panels.append(
                {
                    "arm": arm,
                    "model": model,
                    "condition": condition,
                    "assigned": len(rows),
                    "independent_worlds": len({r["world_id"] for r in rows}),
                    "correct": sum(bool(r.get("correct")) for r in rows),
                    "returned": sum(r.get("transport") == "ok" for r in rows),
                    "reused_receipts": sum(r.get("origin") == "pilot" for r in rows),
                    "supported_correct": sum(bool(r.get("supported")) for r in rows),
                    "valid_actions": sum(bool(r.get("protocol_valid")) for r in rows),
                    "abstentions": sum(bool(r.get("abstained")) for r in rows),
                    "wrong_with_sufficient_evidence": sum(
                        bool(r.get("sufficient_evidence"))
                        and r.get("protocol_valid", False)
                        and not r.get("correct")
                        and not r.get("abstained")
                        for r in rows
                    ),
                    "unsupported_answers": sum(
                        r.get("protocol_valid", False)
                        and not r.get("abstained")
                        and not r.get("sufficient_evidence")
                        for r in rows
                    ),
                    "appropriate_abstentions": sum(
                        bool(r.get("abstained")) and bool(r.get("ambiguous_evidence"))
                        for r in rows
                    ),
                    "known_estimate_microdollars": sum(
                        r.get("actual_microdollars") or 0 for r in rows
                    ),
                    "transport_failures": sum(r.get("transport") != "ok" for r in rows),
                }
            )
        studies[name] = {"provenance": provenance, "panels": panels}
    result = {
        "software_version": VERSION,
        "external_inference": False,
        "model_calls": 0,
        "studies": studies,
        "interpretation": "Separate historical settings; no pooled accuracy or new model inference. Source counts retain every saved assignment including failures.",
    }
    atomic_json(root / "results.json", result)
    write_report(root / "results.json", root / "report")
    if figures:
        from .result_figures import plot_results

        plot_results(result, root)
    return result
