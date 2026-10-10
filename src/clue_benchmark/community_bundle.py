"""Streamed bundle format: case/report rows, not giant JSON arrays.

Large report collections are lazy during construction, writing, and validation.
Atomic seed receipts permit resumable generation; the manifest commits exports.
"""

import hashlib
import json
import os
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from .community_config import SCHEMA_VERSION, CommunityConfig
from .community_generation import (
    _take_owners,
    generate_case,
    iter_allocations,
    iter_nuisance,
    iter_reports,
    merge_evidence,
    public_case,
    render_report,
)
from .community_semantics import (
    Budget,
    certify,
    coalition_certificate,
    core_reports,
    evaluate,
    reliability_profile,
    witness_valid,
)
from .config import VERSION, canonical, digest
from .dataset import atomic_json, fingerprints

FILES = ("cases.jsonl", "partitions.jsonl", "answers.jsonl", "certificates.jsonl")


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def source_hashes():
    return {p.name: file_hash(p) for p in sorted(Path(__file__).parent.glob("*.py"))}


def rows(path):
    with Path(path).open() as stream:
        for line in stream:
            yield json.loads(line)


def _worker(config_dict, seed):
    return generate_case(CommunityConfig.from_dict(config_dict), seed)


def _split(config, case):
    if case["motif_family"] in config.dataset.holdout_families:
        return "transfer"
    value = int(case["world_id"][:16], 16) / 2**64
    edge = 0
    for name in sorted(config.dataset.splits):
        edge += config.dataset.splits[name]
        if value < edge:
            return name
    return sorted(config.dataset.splits)[-1]


def _screen(case):
    compatible = {
        "suspects": case["suspects"],
        "domains": case["domains"],
        "solution": case["solution"],
        "clues": [r["constraint"] for r in core_reports(case["reports"])],
    }
    return fingerprints(compatible)


def generate_dataset(config, tokenizer=None):
    if not isinstance(config, CommunityConfig):
        config = CommunityConfig.from_dict(config)
    if (
        any(
            v is not None
            for v in (
                config.presentation.minimum_tokens,
                config.presentation.maximum_tokens,
            )
        )
        and tokenizer is None
    ):
        raise ValueError("token bounds require Python API tokenizer")
    if tokenizer is not None and config.dataset.workers != 1:
        raise ValueError("custom tokenizer requires workers=1")
    root = Path(config.dataset.output_directory)
    root.mkdir(parents=True, exist_ok=True)
    checkpoints = root / ".community-checkpoints"
    checkpoints.mkdir(exist_ok=True)
    identity = {
        "config_hash": config.fingerprint,
        "sources": source_hashes(),
        "solver_version": __import__(
            "importlib.metadata", fromlist=["version"]
        ).version("ortools"),
    }
    if tokenizer is not None:
        name = getattr(tokenizer, "identity", None)
        if not isinstance(name, str) or not name:
            raise ValueError("custom tokenizer must expose a stable identity string")
        identity["tokenizer_identity"] = name
    identity_path = checkpoints / "identity.json"
    if identity_path.exists() and json.loads(identity_path.read_text()) != identity:
        raise ValueError(
            "checkpoint source/configuration identity changed; use a new output directory"
        )
    atomic_json(identity_path, identity)
    accepted = []
    seen_world, seen_puzzle = set(), set()
    rejects = Counter()
    attempts = []
    maximum = config.dataset.count * config.dataset.max_candidates_per_case
    executor = (
        ProcessPoolExecutor(config.dataset.workers)
        if config.dataset.workers > 1
        else None
    )
    pending = {}

    def submit(index):
        seed = config.dataset.seed + index
        path = checkpoints / f"seed-{seed}.json"
        if executor is not None and not path.exists():
            pending[index] = executor.submit(_worker, config.to_dict(), seed)

    try:
        for i in range(min(config.dataset.workers, maximum)):
            submit(i)
        for i in range(maximum):
            seed = config.dataset.seed + i
            path = checkpoints / f"seed-{seed}.json"
            if path.exists():
                result = json.loads(path.read_text())
            else:
                result = (
                    pending.pop(i).result()
                    if executor
                    else generate_case(config, seed, tokenizer)
                )
                atomic_json(path, result)
            reason = None
            if result["status"] == "ok":
                case = result["case"]
                wh, ph = _screen(case)
                if wh in seen_world or ph in seen_puzzle:
                    reason = "isomorphism_screen_duplicate"
                else:
                    seen_world.add(wh)
                    seen_puzzle.add(ph)
                    accepted.append(path)
            else:
                reason = result["diagnostics"]["reason"]
            attempts.append(
                {
                    "seed": seed,
                    "status": "accepted" if reason is None else result["status"],
                    "rejection": reason,
                }
            )
            if reason:
                rejects[reason] += 1
            if len(accepted) == config.dataset.count:
                break
            submit(
                i + config.dataset.workers
            ) if i + config.dataset.workers < maximum else None
    finally:
        if executor:
            # Preserve all launched receipts, including speculative jobs, so
            # resume never repeats work or loses a failed generation attempt.
            for index, future in pending.items():
                if not future.cancel():
                    atomic_json(
                        checkpoints / f"seed-{config.dataset.seed + index}.json",
                        future.result(),
                    )
            executor.shutdown(wait=True, cancel_futures=True)
    manifest = export_dataset(config, accepted, root)
    manifest.update(
        {
            "complete": len(accepted) == config.dataset.count,
            "attempts": attempts,
            "rejections": dict(rejects),
            "checkpoint_identity": identity,
            "requested_count": config.dataset.count,
        }
    )
    atomic_json(root / "manifest.json", manifest)
    return manifest


def _write(stream, row):
    stream.write(canonical(row) + "\n")


def export_dataset(config, accepted_paths, root):
    handles = {name: (Path(root) / (name + ".tmp")).open("w") for name in FILES}
    worlds, metrics = [], []
    try:
        for path in accepted_paths:
            result = json.loads(Path(path).read_text())
            case, part = result["case"], result["partition"]
            case["split"] = _split(config, case)
            cid = case["case_id"]
            _write(handles["cases.jsonl"], {"kind": "case", **public_case(case)})
            reports = iter_reports(case)
            counts = Counter()
            overlaps = [[0] * case["agent_count"] for _ in range(case["agent_count"])]
            for r, (rid, owners) in zip(
                reports, iter_allocations(case, part), strict=True
            ):
                if r["report_id"] != rid:
                    raise AssertionError("report ownership ordering mismatch")
                _write(
                    handles["cases.jsonl"],
                    {
                        "kind": "report",
                        "case_id": cid,
                        **render_report(r, case, config.presentation),
                    },
                )
                _write(
                    handles["partitions.jsonl"],
                    {
                        "case_id": cid,
                        "report_id": rid,
                        "partition_id": part["partition_id"],
                        "owners": owners,
                    },
                )
                counts.update(owners)
                for left in owners:
                    for right in owners:
                        overlaps[left][right] += 1
            if [counts[i] for i in range(case["agent_count"])] != part[
                "per_agent_quotas"
            ]:
                raise AssertionError("actual allocation does not satisfy quotas")
            if overlaps != part["realized_overlap"]:
                raise AssertionError("actual allocation overlap mismatch")
            _write(
                handles["answers.jsonl"],
                {
                    "case_id": cid,
                    "world_id": case["world_id"],
                    "solution": case["solution"],
                    "possible_culprits": result["certificate"]["candidates"],
                    "false_report_ids": result["certificate"]["false_report_ids"],
                    "nuisance_count": case["nuisance_count"],
                    "core_report_ids": [r["report_id"] for r in case["reports"]],
                },
            )
            certificate = {**result["certificate"], "case_hash": digest(case)}
            _write(
                handles["certificates.jsonl"],
                {
                    "case_id": cid,
                    "certificate": certificate,
                    "partition": {k: v for k, v in part.items() if k != "certificate"},
                },
            )
            worlds.append(
                {
                    "world_id": case["world_id"],
                    "case_id": cid,
                    "split": case["split"],
                    "family": case["motif_family"],
                    "seed": case["seed"],
                    "presentation_id": case["presentation_id"],
                }
            )
            metrics.append(
                {
                    "case_id": cid,
                    **case["presentation_metrics"],
                    "total_reports": len(case["reports"]) + case["nuisance_count"],
                    "core_reports": len(case["reports"]),
                    "nuisance_records": case["nuisance_count"],
                    "unique_facts": len(case["reports"]) + case["nuisance_count"],
                    "repeated_presentations": 0,
                    "shared_fraction": part["shared_fraction"],
                    "private_fraction": part["private_fraction"],
                    "realized_overlap": overlaps,
                    "necessary_evidence": certificate["minimum_subset"],
                    **result["diagnostics"],
                }
            )
    finally:
        for stream in handles.values():
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
    for name in FILES:
        (Path(root) / (name + ".tmp")).replace(Path(root) / name)
    return {
        "schema_version": SCHEMA_VERSION,
        "software_version": VERSION,
        "solver_version": __import__(
            "importlib.metadata", fromlist=["version"]
        ).version("ortools"),
        "config": config.to_dict(),
        "config_hash": config.fingerprint,
        "files": {name: file_hash(Path(root) / name) for name in FILES},
        "worlds": worlds,
        "metrics": metrics,
        "external_inference": False,
        "language_review": "pending",
        "licensing": "pending",
        "independent_reproduction": "pending",
        "public_release_ready": False,
        "format": "cases.jsonl contains one case header followed by independently streamed report rows",
    }


def verify_manifest(root):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest["schema_version"] != SCHEMA_VERSION or set(manifest["files"]) != set(
        FILES
    ):
        raise ValueError("invalid bundle manifest")
    for name, expected in manifest["files"].items():
        if file_hash(root / name) != expected:
            raise ValueError("bundle hash mismatch: " + name)
    return manifest


def iter_cases(root, agent_id=None):
    """Public-only streaming records, optionally filtered to one agent."""
    root = Path(root)
    verify_manifest(root)
    allocations = iter(rows(root / "partitions.jsonl"))
    current = None
    for r in rows(root / "cases.jsonl"):
        if r["kind"] == "case":
            current = r
            if agent_id is not None and (
                type(agent_id) is not int or not 0 <= agent_id < r["agent_count"]
            ):
                raise ValueError("invalid agent id")
            yield r
        else:
            a = next(allocations)
            if (
                current is None
                or a["case_id"] != r["case_id"]
                or a["report_id"] != r["report_id"]
            ):
                raise ValueError("public report/partition mismatch")
            if agent_id is None or agent_id in a["owners"]:
                yield r


def load_evaluator_cases(root):
    """Only core reports retained; large nuisance records validated separately."""
    root = Path(root)
    manifest = verify_manifest(root)
    answers = {r["case_id"]: r for r in rows(root / "answers.jsonl")}
    certificates = {r["case_id"]: r for r in rows(root / "certificates.jsonl")}
    allocations = iter(rows(root / "partitions.jsonl"))
    presentation = CommunityConfig.from_dict(manifest["config"]).presentation
    current = None

    def finish():
        if (
            observed != current["saved_certificate"]["partition"]["per_agent_quotas"]
            or any(remaining)
            or overlap != part["realized_overlap"]
        ):
            raise ValueError("actual report ownership violates certified quotas")
        if next(expected_ids, None) is not None:
            raise ValueError("missing reports in presentation sequence")

    for row in iter_cases(root):
        if row["kind"] == "case":
            if current is not None:
                finish()
                yield current
            answer = answers[row["case_id"]]
            current = {
                **row,
                "reports": [],
                "solution": answer["solution"],
                "false_report_count": len(answer["false_report_ids"]),
                "nuisance_count": answer["nuisance_count"],
                "saved_certificate": certificates[row["case_id"]],
                "config": manifest["config"],
                "actual_nuisance": 0,
            }
            if presentation.evidence_placement != "front":
                current["evidence_placement"] = presentation.evidence_placement
            expected_ids = iter(
                merge_evidence(
                    answer["core_report_ids"],
                    (r["report_id"] for r in iter_nuisance(current)),
                    current["nuisance_count"],
                    presentation.evidence_placement,
                )
            )
            part = current["saved_certificate"]["partition"]
            if (
                digest({k: v for k, v in part.items() if k != "partition_id"})
                != part["partition_id"]
            ):
                raise ValueError("certified partition identity mismatch")
            recipe = part["nuisance_recipe"]
            if (
                recipe["count"] != current["nuisance_count"]
                or recipe["agent_count"] != current["agent_count"]
            ):
                raise ValueError("nuisance ownership recipe mismatch")
            remaining = list(recipe["remaining_quotas"])
            observed = [0] * current["agent_count"]
            overlap = [
                [0] * current["agent_count"] for _ in range(current["agent_count"])
            ]
            records_left = recipe["count"] - recipe["shared_prefix"]
            continue
        allocation = next(allocations)
        if row["report_id"] != next(expected_ids, None):
            raise ValueError("report ordering differs from published presentation")
        if row["text"] != render_report(row, current, presentation)["text"]:
            raise ValueError("rendered report does not match structured constraint")
        if row["constraint"]["type"] == "record_positive":
            c = row["constraint"]
            if (
                set(c) != {"type", "component", "variable", "value", "domain"}
                or c["variable"] != "value"
                or c["domain"] != ["0", "1"]
                or c["value"] != str(current["actual_nuisance"] % 2)
            ):
                raise ValueError("invalid nuisance record")
            # Match the deterministic fresh namespace without retaining all IDs.
            component = digest(
                [current["world_id"], "component", current["actual_nuisance"]]
            )
            if c["component"] != component or row["report_id"] != digest(c):
                raise ValueError("invalid nuisance identity")
            if current["actual_nuisance"] < recipe["shared_prefix"]:
                owners = list(range(current["agent_count"]))
            else:
                owners = _take_owners(
                    remaining, records_left, recipe["private_replication"]
                )
                records_left -= 1
            current["actual_nuisance"] += 1
        else:
            current["reports"].append({k: row[k] for k in ("report_id", "constraint")})
            owners = part["core_allocation"][row["report_id"]]
        if (
            allocation["owners"] != owners
            or allocation["partition_id"] != part["partition_id"]
        ):
            raise ValueError("actual report ownership differs from certified partition")
        for agent in owners:
            observed[agent] += 1
            for other in owners:
                overlap[agent][other] += 1
    if current is not None:
        finish()
        yield current
    if next(allocations, None) is not None:
        raise ValueError("unexpected extra report ownership rows")


def validate_dataset(root):
    manifest = verify_manifest(root)
    results = []
    world_splits = {}
    for case in load_evaluator_cases(root):
        cid = case["case_id"]
        if (
            case["actual_nuisance"] != case["nuisance_count"]
            or len(case["reports"]) + case["nuisance_count"] != case["total_reports"]
        ):
            raise ValueError("report count mismatch")
        if any(r["report_id"] != digest(r["constraint"]) for r in case["reports"]):
            raise ValueError("core report identity mismatch")
        if (
            case["world_id"] in world_splits
            and world_splits[case["world_id"]] != case["split"]
        ):
            raise ValueError("world variants cross splits")
        world_splits[case["world_id"]] = case["split"]
        cfg = CommunityConfig.from_dict(manifest["config"])
        budget = Budget(cfg.dataset.certification_seconds, cfg.dataset.max_solver_calls)
        fresh = certify(case, budget)
        saved = case["saved_certificate"]
        if (
            case["false_report_count"] != cfg.evidence.false_reports
            or case["corruption_allowance"] != cfg.evidence.corruption_allowance
            or fresh["status"] != "verified_" + cfg.evidence.answerability
            or len(case["reports"])
            != cfg.puzzle.config["clue_count"]
            + cfg.evidence.entailed_clues
            + cfg.evidence.connected_decoys
        ):
            raise ValueError("evidence does not satisfy resolved configuration")
        if (
            cfg.puzzle.family == "redundant_paths"
            or cfg.evidence.maximum_alternative_margin is not None
            or (
                cfg.evidence.corruption_strategy == "targeted"
                and cfg.evidence.false_reports
            )
        ) and "reliability_profile" not in saved["certificate"]:
            raise ValueError("required reliability profile missing")
        decoys = saved["certificate"].get("connected_decoys")
        if cfg.evidence.connected_decoys:
            if not decoys or len(decoys["reports"]) != cfg.evidence.connected_decoys:
                raise ValueError("connected decoy count mismatch")
            truthful = {
                **case,
                "reports": decoys["truthful_basis"],
                "corruption_allowance": 0,
            }
            if any(
                r["report_id"] != digest(r["constraint"]) for r in truthful["reports"]
            ) or not witness_valid(
                truthful, case["solution"]["world"], case["solution"]["murderer"]
            ):
                raise ValueError(
                    "connected decoy basis incompatible with sampled world"
                )
            if evaluate(truthful, budget=budget)["candidates"] != [
                case["solution"]["murderer"]
            ]:
                raise ValueError("connected decoy basis is not a truthful unique core")
            restored = {r["report_id"] for r in case["reports"]}
            for change in saved["certificate"]["corruptions"]:
                restored.remove(change["false_report_id"])
                restored.add(change["original_report_id"])
            if restored != {
                r["report_id"] for r in decoys["truthful_basis"] + decoys["reports"]
            }:
                raise ValueError("connected decoys do not match the original evidence")
            for report in decoys["reports"]:
                c = report["constraint"]
                if c["type"] not in (
                    "suspect_same_as",
                    "suspect_different_from",
                ) or report["report_id"] != digest(c):
                    raise ValueError("invalid connected relational decoy")
                negation = {
                    **c,
                    "type": "suspect_different_from"
                    if c["type"] == "suspect_same_as"
                    else "suspect_same_as",
                }
                if evaluate(
                    truthful,
                    truthful["reports"]
                    + [{"report_id": digest(negation), "constraint": negation}],
                    budget,
                )["candidates"]:
                    raise ValueError("connected decoy not entailed by truthful basis")
        if (
            fresh["candidates"] != saved["certificate"]["candidates"]
            or fresh["false_report_ids"] != saved["certificate"]["false_report_ids"]
        ):
            raise ValueError("saved answer certificate mismatch")
        part = saved["partition"]
        if "reliability_profile" in saved["certificate"]:
            profile = reliability_profile(case, budget)
            stored = saved["certificate"]["reliability_profile"]
            for r in stored["candidates"]:
                if not witness_valid(
                    {**case, "corruption_allowance": r["minimum_violations"]},
                    r["world"],
                    r["culprit"],
                ):
                    raise ValueError("saved reliability witness invalid")
            if profile["alternative_margin"] != stored["alternative_margin"] or [
                (r["culprit"], r["minimum_violations"]) for r in profile["candidates"]
            ] != [
                (r["culprit"], r["minimum_violations"]) for r in stored["candidates"]
            ]:
                raise ValueError("saved reliability distance mismatch")
            if cfg.evidence.maximum_alternative_margin is not None and (
                profile["alternative_margin"] > cfg.evidence.maximum_alternative_margin
            ):
                raise ValueError("alternative margin exceeds requested bound")
        coalition = coalition_certificate(case, part["core_allocation"], budget)
        if coalition != saved["certificate"]["coalition"]:
            # Witnesses can change without changing semantic answers.
            keys = ("minimum_size", "minimal_sufficient_coalitions", "allocation_hash")
            if any(
                coalition[k] != saved["certificate"]["coalition"][k] for k in keys
            ) or any(
                a["candidates"] != b["candidates"]
                for a, b in zip(
                    coalition["coalitions"],
                    saved["certificate"]["coalition"]["coalitions"],
                    strict=True,
                )
            ):
                raise ValueError("saved coalition certificate mismatch")
        optimum = saved["certificate"]["minimum_subset"]
        if optimum["upper_bound"] is not None:
            subset = [
                r for r in case["reports"] if r["report_id"] in optimum["report_ids"]
            ]
            if len(subset) != optimum["upper_bound"] or evaluate(case, subset, budget)[
                "candidates"
            ] != [case["solution"]["murderer"]]:
                raise ValueError("minimum subset upper bound invalid")
            _validate_lower_bound(case, optimum, budget)
        results.append(
            {
                "case_id": cid,
                "status": fresh["status"],
                "coalition_status": coalition["status"],
            }
        )
    if len(results) != len(manifest["worlds"]):
        raise ValueError("manifest case coverage mismatch")
    return {"status": "verified", "cases": results, "public_release_ready": False}


def _validate_lower_bound(case, optimum, budget):
    from ortools.sat.python import cp_model

    from .independent_oracle import holds

    by_id = {r["report_id"]: r for r in core_reports(case["reports"])}
    order = optimum["report_order"]
    if len(order) != len(by_id) or set(order) != set(by_id):
        raise ValueError("invalid optimum report order")
    reports = [by_id[rid] for rid in order]
    master = cp_model.CpModel()
    bits = [master.new_bool_var(str(i)) for i in range(len(reports))]
    for cut in optimum.get("cuts", []):
        culprit, world = cut["culprit"], cut["world"]
        if culprit == case["solution"]["murderer"] or not witness_valid(
            {**case, "corruption_allowance": len(reports)}, world, culprit, []
        ):
            raise ValueError("invalid optimum countermodel")
        violated = [
            i
            for i, r in enumerate(reports)
            if not holds(r["constraint"], world, culprit)
        ]
        if violated != cut["violated"]:
            raise ValueError("invalid multicover cut")
        master.add(sum(bits[i] for i in violated) > case["corruption_allowance"])
    master.add(sum(bits) < optimum["lower_bound"])
    if budget.solve(master)[0] != cp_model.INFEASIBLE:
        raise ValueError("minimum subset lower bound unproved")
    if (
        optimum["status"] == "exact"
        and optimum["lower_bound"] != optimum["upper_bound"]
    ):
        raise ValueError("exact bound mismatch")


def profile_dataset(config):
    started = time.monotonic()
    result = generate_dataset(config)
    root = Path(result["config"]["dataset"]["output_directory"])
    return {
        "complete": result["complete"],
        "elapsed_seconds": time.monotonic() - started,
        "storage_bytes": sum((root / name).stat().st_size for name in FILES),
        "cases": result["metrics"],
        "attempts": len(result["attempts"]),
        "rejections": result["rejections"],
        "scaling_claim": "total corpus volume; necessary-evidence certificate reported separately",
    }
