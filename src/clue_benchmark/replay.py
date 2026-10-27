"""Keyless reproduction fixtures and accessible local reports."""

import html
import json
import shutil
from collections import Counter
from importlib.resources import as_file, files
from pathlib import Path

from .community_bundle import file_hash, load_evaluator_cases, validate_dataset
from .community_evaluation import _observations
from .community_semantics import evaluate
from .config import VERSION
from .dataset import atomic_json


def replay_example(name, output):
    if name != "distributed-evidence":
        raise ValueError("available offline example: distributed-evidence")
    destination = Path(output)
    if destination.exists():
        raise ValueError("replay output exists; choose a new directory")
    source = files("clue_benchmark").joinpath("resources", name)
    with as_file(source) as directory:
        shutil.copytree(directory, destination)
    validate_dataset(destination)
    manifest = json.loads((destination / "manifest.json").read_text())
    episodes = []
    for case in load_evaluator_cases(destination):
        plan = {
            "dataset_config": manifest["config"],
            "prompt": "Identify the responsible suspect.",
            "models": [{"context_tokens": 1048576}],
            "graph": "star",
            "rounds": 1,
            "max_reports_per_message": 64,
        }
        for condition in ("complete", "independent", "sharing"):
            for agent, _, evidence, messages, _ in _observations(case, plan, condition):
                candidates = evaluate(case, evidence)["candidates"]
                episodes.append(
                    {
                        "world_id": case["world_id"],
                        "case_id": case["case_id"],
                        "condition": condition,
                        "agent": agent,
                        "possible_answers": len(candidates),
                        "sufficient": len(candidates) == 1,
                        "messages": len(messages),
                    }
                )
    result = {
        "software_version": VERSION,
        "study_id": "distributed-evidence-offline-controls",
        "source_manifest_sha256": file_hash(destination / "manifest.json"),
        "independent_worlds": len(manifest["worlds"]),
        "assignments": len(episodes),
        "model_calls": 0,
        "external_inference": False,
        "interpretation": "Solver availability controls on historical worlds; not a rerun of model inference. Forwarding is programmed.",
        "episodes": episodes,
    }
    atomic_json(destination / "replay.json", result)
    write_report(destination / "replay.json", destination / "report")
    return result


def _panel_table(title, panels):
    columns = [
        "burden",
        "model",
        "dose",
        "worlds",
        "assigned",
        "supported_correct",
        "assigned_accuracy",
        "abstentions",
        "settled_estimate_microdollars",
    ]
    table = (
        "<h2>"
        + html.escape(title)
        + "</h2><div role='region' aria-label='Scrollable results table' tabindex='0' style='overflow:auto'><table><caption>Every assigned slot retained; worlds are independent units</caption><thead><tr>"
    )
    table += (
        "".join(
            "<th scope='col'>" + html.escape(c.replace("_", " ")) + "</th>"
            for c in columns
        )
        + "</tr></thead><tbody>"
    )
    for panel in panels:
        table += (
            "<tr>"
            + "".join(
                "<td>" + html.escape(str(panel.get(c, "unavailable"))) + "</td>"
                for c in columns
            )
            + "</tr>"
        )
    return table + "</tbody></table></div>"


def write_report(source, output):
    """Render arbitrary saved JSON safely; never interprets HTML from a model."""
    source = Path(source)
    value = json.loads(source.read_text())
    if not isinstance(value, dict):
        raise ValueError("report source must be a JSON object")
    records = value.get("episodes", [])
    if not isinstance(records, list) or any(
        not isinstance(row, dict) for row in records
    ):
        raise ValueError("report episodes must be a list of JSON objects")
    studies = value.get("studies", {})
    if not isinstance(studies, dict) or any(
        not isinstance(study, dict)
        or not isinstance(study.get("panels"), list)
        or not isinstance(study.get("provenance"), dict)
        or not isinstance(study.get("provenance", {}).get("limitations"), str)
        or any(not isinstance(panel, dict) for panel in study["panels"])
        for study in studies.values()
    ):
        raise ValueError(
            "report studies must contain panel objects and provenance limitations"
        )
    if "panels" in value and (
        not isinstance(value["panels"], list)
        or any(not isinstance(panel, dict) for panel in value["panels"])
    ):
        raise ValueError("report panels must be a list of JSON objects")
    if any(
        ("world_id" in row and not isinstance(row["world_id"], str))
        or ("condition" in row and not isinstance(row["condition"], str))
        for row in records
    ):
        raise ValueError("report world_id and condition values must be strings")
    phases = value.get("phases", {})
    if not isinstance(phases, dict) or any(
        not isinstance(phase, dict)
        or not isinstance(phase.get("panels"), list)
        or any(not isinstance(panel, dict) for panel in phase["panels"])
        for phase in phases.values()
    ):
        raise ValueError("report phases must contain panel objects")
    destination = Path(output)
    destination.mkdir(parents=True, exist_ok=False)
    counts = Counter(r.get("condition", "unspecified") for r in records)
    summary = {
        "software_version": VERSION,
        "source_sha256": file_hash(source),
        "source_name": source.name,
        "independent_worlds": len({r["world_id"] for r in records if "world_id" in r}),
        "assigned_records": len(records),
        "conditions": dict(counts),
        "external_inference": False,
    }
    if (
        not records
        and isinstance(value.get("assigned_slots"), int)
        and isinstance(value.get("independent_worlds"), int)
    ):
        summary["assigned_records"] = value["assigned_slots"]
        summary["independent_worlds"] = value["independent_worlds"]
    if "limitations" in value:
        summary["limitations"] = str(value["limitations"])
    if isinstance(value.get("accounting"), dict):
        summary["accounting"] = value["accounting"]
    panels_html = ""
    if "studies" in value:
        summary.pop("independent_worlds")
        summary.pop("assigned_records")
        summary.pop("conditions")
        summary["studies"] = len(value["studies"])
        columns = [
            "arm",
            "model",
            "condition",
            "independent_worlds",
            "assigned",
            "correct",
            "supported_correct",
            "valid_actions",
            "abstentions",
            "known_estimate_microdollars",
        ]
        for name, study in value["studies"].items():
            panels_html += (
                "<h2>"
                + html.escape(name)
                + "</h2><p>"
                + html.escape(study["provenance"]["limitations"])
                + "</p><div style='overflow:auto'><table><caption>Separate settings and assigned denominators</caption><thead><tr>"
            )
            panels_html += (
                "".join(
                    "<th scope='col'>" + html.escape(c.replace("_", " ")) + "</th>"
                    for c in columns
                )
                + "</tr></thead><tbody>"
            )
            for panel in study["panels"]:
                panels_html += (
                    "<tr>"
                    + "".join(
                        "<td>" + html.escape(str(panel.get(c, "unavailable"))) + "</td>"
                        for c in columns
                    )
                    + "</tr>"
                )
            panels_html += "</tbody></table></div>"
    for phase, saved in phases.items():
        if saved["panels"]:
            panels_html += _panel_table(str(phase).title() + " phase", saved["panels"])
    if value.get("panels"):
        panels_html += _panel_table(
            "Combined exploratory estimate" if phases else "Per-condition results",
            value["panels"],
        )
    atomic_json(destination / "report.json", {"summary": summary, "source": value})
    shutil.copyfile(source, destination / "source.json")
    rows = "".join(
        f"<tr><th scope='row'>{html.escape(k)}</th><td>{html.escape(str(v))}</td></tr>"
        for k, v in summary.items()
    )
    text = (
        "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>Clue Benchmark offline report</title><style>body{font:1rem system-ui;max-width:70rem;margin:auto;padding:2rem}table{border-collapse:collapse}td,th{padding:.6rem;border:1px solid #777;text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere}a:focus{outline:3px solid #36c}</style><main><h1>Offline evidence report</h1><p>Assigned records are not independent worlds. Missing records are not observed failures.</p><table><caption>Source and denominators</caption>"
        + rows
        + "</table><p><a href='source.json'>Download exact source JSON</a></p>"
        + panels_html
        + "<details><summary>Inspect all saved observations and outcomes</summary><pre>"
        + html.escape(json.dumps(value, indent=2, ensure_ascii=False))
        + "</pre></details></main></html>"
    )
    (destination / "index.html").write_text(text)
    return summary
