"""Build an auditable, descriptive continuation report from saved exports only."""

import argparse
import hashlib
import itertools
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from clue_benchmark.dataset import atomic_json, read_cases
from clue_benchmark.investigation import clustered_interval

MISSING = {"missing_episode", "interrupted_episode", "in_progress"}
UNFUNDED = MISSING | {"budget_stopped"}


def rate(rows, key="correct"):
    return sum(r.get(key, 0) for r in rows) / len(rows) if rows else None


def ci(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row["world_group"]].append(row["correct"])
    return (
        clustered_interval([sum(x) / len(x) for x in groups.values()])
        if groups
        else None
    )


def describe(rows):
    finished = [r for r in rows if r["error"] not in MISSING]
    completed = [r for r in finished if r["completion"]]
    return {
        "declared": len(rows),
        "finished": len(finished),
        "correct": sum(r["correct"] for r in rows),
        "declared_accuracy": rate(rows),
        "declared_world_cluster_ci95": ci(rows),
        "dispatch_coverage": len(finished) / len(rows),
        "completed_submissions": len(completed),
        "missing_submissions_among_finished": sum(
            r["missing_submission"] for r in finished
        ),
        "invalid_actions": sum(r["invalid_actions"] for r in finished),
        "errors_among_finished": dict(Counter(r["error"] or "none" for r in finished)),
        "accuracy_among_completed": rate(completed),
        "mean_seconds_among_finished": sum(r["seconds"] for r in finished)
        / len(finished)
        if finished
        else None,
        "mean_clues_among_finished": sum(r["spent"] for r in finished) / len(finished)
        if finished
        else None,
        "mean_requests_among_finished": sum(r["requests"] for r in finished)
        / len(finished)
        if finished
        else None,
    }


def complete_worlds(rows, models):
    """Keep whole world schedules, including scored failures, without success selection."""
    worlds = defaultdict(list)
    for row in rows:
        if row["model"] in models:
            worlds[row["world_group"]].append(row)
    return sorted(
        w
        for w, group in worlds.items()
        if len(group) == 18 * len(models)
        and all(r["error"] not in UNFUNDED for r in group)
        and {r["model"] for r in group} == set(models)
    )


def paired(rows, models):
    output = []
    lookup = {
        (
            r["model"],
            r["case_id"],
            r["track"],
            r["selection_policy"],
            r["budget_fraction"],
            r["repeat"],
        ): r
        for r in rows
    }
    for a, b in itertools.combinations(models, 2):
        for n in (4, 8, 12):
            for track, policy, budget in [("deduction", "agent", 1.0)] + [
                ("investigation", p, x)
                for p in ("agent", "random")
                for x in (0.25, 0.5, 0.75, 1.0)
            ]:
                values = defaultdict(list)
                for row in rows:
                    if (
                        row["model"],
                        row["suspects"],
                        row["track"],
                        row["selection_policy"],
                        row["budget_fraction"],
                    ) != (a, n, track, policy, budget):
                        continue
                    other = lookup[
                        (b, row["case_id"], track, policy, budget, row["repeat"])
                    ]
                    values[row["world_group"]].append(row["correct"] - other["correct"])
                means = [sum(v) / len(v) for v in values.values()]
                if means:
                    output.append(
                        {
                            "model_a": a,
                            "model_b": b,
                            "suspects": n,
                            "track": track,
                            "selection_policy": policy,
                            "budget_fraction": budget,
                            "worlds": len(means),
                            "accuracy_a_minus_b": sum(means) / len(means),
                            "world_cluster_ci95": clustered_interval(means),
                        }
                    )
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("plan")
    parser.add_argument("--root", default=".")
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    plan = json.loads(Path(args.plan).read_text())
    output = root / plan["execution_directory"]
    raw = (output / "results.json").read_bytes()
    result = json.loads(raw)
    assert result["manifest"]["plan_id"] == plan["plan_id"]
    diagnostics = json.loads((output / "evidence-diagnostics.json").read_text())
    if diagnostics.get("results_sha256") != hashlib.sha256(raw).hexdigest():
        raise ValueError("evidence diagnostics do not match the current result export")
    rows, ledger = result["episodes"], result["ledger"]
    assert ledger["ceiling_usd"] == 25 and ledger["committed_usd"] <= 25
    assert all(
        r["case_id"]
        in set(plan["datasets"]["dev"].get("case_ids", plan["selected_case_ids"]))
        for r in rows
    )
    cohorts = {}
    plot_cells = []
    for cohort in ("initial_pilot", "expanded_development"):
        part = [r for r in rows if r["analysis_cohort"] == cohort]
        models = [m for m in plan["models"] if any(r["model"] == m for r in part)]
        shared = complete_worlds(part, models)
        shared_rows = [r for r in part if r["world_group"] in shared]
        by_model = {}
        for model in models:
            own = [r for r in part if r["model"] == model]
            diag = [
                r
                for r in diagnostics["rows"]
                if r["analysis_cohort"] == cohort and r["model"] == model
            ]
            known = [r for r in diag if r["diagnostic_error"] is None]
            by_model[model] = {
                **describe(own),
                "deduction": describe([r for r in own if r["track"] == "deduction"]),
                "diagnosed": len(diag),
                "identifying_evidence": sum(r["identifying_evidence"] for r in known),
                "inconsistent_submitted_answers": sum(
                    r.get("submitted_answer_consistent") is False for r in known
                ),
            }
            # Initial graphs use fully dispatched cells; expansion uses whole matched world schedules.
            plotted = (
                own
                if cohort == "initial_pilot"
                else [r for r in shared_rows if r["model"] == model]
            )
            for n in (4, 8, 12):
                for track, policy, budget in [("deduction", "agent", 1.0)] + [
                    ("investigation", p, x)
                    for p in ("agent", "random")
                    for x in (0.25, 0.5, 0.75, 1.0)
                ]:
                    group = [
                        r
                        for r in plotted
                        if (
                            r["suspects"],
                            r["track"],
                            r["selection_policy"],
                            r["budget_fraction"],
                        )
                        == (n, track, policy, budget)
                    ]
                    if group and all(r["error"] not in UNFUNDED for r in group):
                        plot_cells.append(
                            {
                                "cohort": cohort,
                                "model": model,
                                "suspects": n,
                                "track": track,
                                "selection_policy": policy,
                                "budget_fraction": budget,
                                "episodes": len(group),
                                "worlds": len({r["world_group"] for r in group}),
                                "correct": sum(r["correct"] for r in group),
                                "accuracy": rate(group),
                                "ci95": ci(group),
                            }
                        )
        cohorts[cohort] = {
            "models": by_model,
            "fully_attempted_shared_worlds": shared,
            "post_hoc_matched_world_model_gaps": paired(shared_rows, models),
            "post_hoc_matched_world_method": "Retain both density variants and all nine conditions for every shared model. Keep token/protocol/service failures incorrect. Exclude unrun, in-progress and funding-stopped world schedules; no filtering on correctness or completion. This is post-hoc and not a primary population comparison.",
        }
    cases = read_cases(root / plan["datasets"]["dev"]["path"])
    initial = set(plan["initial_pilot_case_ids"])
    labels = defaultdict(dict)
    for c in cases:
        cohort = "initial_pilot" if c["case_id"] in initial else "expanded_development"
        labels[(cohort, len(c["suspects"]))][c["world_group"]] = c["solution"][
            "murderer"
        ]
    label_summary = [
        {
            "cohort": k[0],
            "suspects": k[1],
            "worlds": len(v),
            "murderer_labels": dict(sorted(Counter(v.values()).items())),
            "best_constant_label_accuracy": max(Counter(v.values()).values()) / len(v),
        }
        for k, v in sorted(labels.items())
    ]
    held = sum(q["reserved"] for q in ledger["requests"] if q["status"] == "held") / 1e6
    outstanding = (
        sum(
            q["reserved"]
            for q in ledger["requests"]
            if q["status"] in ("reserved", "uncertain")
        )
        / 1e6
    )
    violations = [
        q["id"]
        for q in ledger["requests"]
        if q.get("config")
        and q.get("usage")
        and (
            q["usage"]["total_tokens"] > q["config"]["remaining_episode_tokens"]
            or q["usage"]["output_tokens"] > q["config"]["output_cap"]
        )
    ]
    analysis = {
        "plan_id": plan["plan_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_kind": "final" if args.final else "interim",
        "results_sha256": hashlib.sha256(raw).hexdigest(),
        "generation_calls": 0,
        "paid_ceiling_usd": 25,
        "second_allocation_executed": False,
        "settled_usd": ledger["settled_usd"],
        "held_usd": held,
        "inflight_or_uncertain_usd": outstanding,
        "committed_usd": ledger["committed_usd"],
        "remaining_usd": ledger["remaining_usd"],
        "cohorts": cohorts,
        "plot_cells": plot_cells,
        "label_distribution": label_summary,
        "continued_request_allowance_violations": violations,
        "limitations": [
            "Exploratory development evaluation with historical amendments; no clean capability ranking",
            "Random evidence and native investigation differ in interaction and thinking overhead",
            "Whole declared denominators count unrun and failed rows incorrect; dispatch coverage must accompany accuracy",
            "Conditional and post-hoc complete-world statistics may be selected and are descriptive",
            "One repeat and few independent worlds; degenerate bootstrap intervals do not establish population perfection",
            "Label imbalance and awkward controlled-English clues can affect performance",
            "Token stops and missing native final submissions confound output correctness with resource/protocol constraints",
        ],
    }
    atomic_json(output / "analysis-summary.json", analysis)
    lines = [
        "# First-$25 development continuation",
        "",
        f"Snapshot: **{'final saved run' if args.final else 'interim; model execution is still in progress'}**, generated {analysis['generated_at_utc']}. The frozen cumulative Gemini ceiling is **$25**, including the original pilot and all held requests. The other $25 has not been used.",
        "",
        f"Estimated returned-usage API charges: **${ledger['settled_usd']:.6f}**. Held failed-request maxima: **${held:.6f}**. In-flight or uncertain reservations: ${outstanding:.6f}. Total committed allowance: **${ledger['committed_usd']:.6f}**; remaining ${ledger['remaining_usd']:.6f}. These use frozen standard token prices and are not invoice reconciliation. Local energy and hardware costs are excluded.",
        "",
        f"Frozen manifest: `{plan['plan_id']}`. Native request count: {len(ledger['requests'])}. Declared rows: {len(rows)}. All 744 test cases remain unexecuted by models.",
        "",
        "## Coverage and complete-evidence deduction",
        "",
        "The initial cohort contains the original 12 paired worlds (24 cases), 216 rows per model. The expansion contains 96 additional paired worlds, 1,728 rows per Gemini model. Qwen/Gemini comparisons use the initial shared cohort only. The larger expansion excludes the diagnostic worlds.",
        "",
    ]
    for cohort, entry in cohorts.items():
        lines += [f"### {cohort.replace('_', ' ').capitalize()}", ""]
        for model, stats in entry["models"].items():
            d = stats["deduction"]
            lines.append(
                f"- **{model}**: {stats['finished']}/{stats['declared']} finished; {stats['completed_submissions']} completed submissions; {stats['correct']}/{stats['declared']} correct in the declared denominator. Complete-evidence deduction: {d['correct']}/{d['declared']} correct, {d['finished']} finished. Finished-row errors: {stats['errors_among_finished']}. Evidence diagnostics: {stats['identifying_evidence']}/{stats['diagnosed']} identifying; {stats['inconsistent_submitted_answers']} submitted answers inconsistent with revealed evidence."
            )
        lines += [
            "",
            f"Fully attempted world schedules shared by all models in this cohort: **{len(entry['fully_attempted_shared_worlds'])}**. Paired gaps and world-clustered 95% intervals are in analysis-summary.json. This additional comparison is post-hoc; scored failures remain incorrect and no worlds are filtered by answer success.",
            "",
        ]
    lines += [
        "## Budget curves and interpretation",
        "",
        "![Initial pilot budget curves](../results/pilot-v0.3-continued/initial-pilot-curves.png)",
        "",
        "![Initial complete-evidence deduction](../results/pilot-v0.3-continued/initial-pilot-deduction.png)",
        "",
        "The figures plot only fully attempted cells. Missing cells are explicitly unplotted. Failed attempts count incorrect. Expansion figures, when available, use whole world schedules attempted by both Gemini models. Primary declared-denominator accuracy, evidence-budget averages, mean clues/requests, invalid actions, completion, tokens, costs, latency, and paired strategy/model gaps remain in results.json. All related variants and conditions remain in their world cluster for uncertainty estimates. Uniform outcomes can give degenerate intervals; these do not imply perfect population accuracy.",
        "",
        "Investigation makes successive native tool calls, while random controls receive their selected clues before answering. Their contrast includes conversation and thinking overhead and cannot isolate topic-selection quality. Cumulative 32,768 input-plus-output tokens count repeated conversation history, and the 4,096 per-call output maximum includes thinking. Report resource and submission failures alongside accuracy; this run does not establish a clean model ranking.",
        "",
        "## Evidence and representative failures",
        "",
        "Evidence diagnostics reconstruct exactly the successful clue reveals in each native transcript and use structured versions of those clues to enumerate feasible murderer candidates. No private world attributes or unrevealed clues are used for inference. These diagnostics are evaluator-only and post-hoc. Unresolved solver results remain unknown. A wrong feasible suspect with several remaining candidates differs from an answer excluded by the revealed evidence. Conditional accuracy after identifying evidence is descriptive and subject to selection.",
        "",
        "manual-review.json retains the six original examples and four continuation examples. Reviewed Qwen submissions in four- and eight-suspect cases directly contradict a crime_different_from clue naming the submitted suspect. Another twelve-suspect complete-evidence episode ended with 4,096 generated tokens, empty content, no final tool call and no answer. Internal thinking is not available; these examples establish observable output failures, not the model's cognitive process. They are selected Codex reviews, not independent human annotations or a prevalence estimate.",
        "",
        "## Accounting and execution amendments",
        "",
        "The continuation copied all 82 historical episodes and 213 requests into an audited durable ledger. Original request 213 is user-reported HTTP 503; its full $0.324813 maximum remains held. Native 503 failures retain their maximum reservations and failed scores, with no automatic retry. The user subsequently authorized retaining full maximum charges for failed timeouts, then explicitly approved applying the same maximum-charge holds to unverifiable successful-response usage. These remain failed scored episodes with unknown actual usage and charges, never zero-cost assumptions. Other unclassified unresolved errors and native incompatibilities still stop execution. Paid and free local execution have independent locks; all paid requests remain sequential.",
        "",
        "The revised preflight adds 12.5% plus 1,024-token headroom, and bounds native thinking history using prior reported usage. Each new request records the input bound, output cap, and remaining cumulative allowance. Actual reported violations still stop the model. Historical cap violations and SDK failures remain scored and preserved. accounting-recovery.json records each held timeout and restored model. The current frozen controller identity is in studies/pilot-v0.3-reserved-recovery.json; no failed episode or request is replayed. Qwen was already running with the preceding manifest and unchanged native source/settings; aggregate exports bind all preserved rows to the current plan, with each row retaining its execution source identity.",
        "",
        f"Observed new request allowance violations in this export: **{len(violations)}**. Outstanding accounting holds and runtime model states remain visible in cost-ledger.json. Original source snapshots, manifest amendments and results are preserved.",
        "",
        "## What to change before the second $25",
        "",
        "1. Match the answer-stage evidence context and generation allowance across agent and random selections. A two-stage design can select clues first, then answer from a fresh standardized context. Retain an end-to-end resource-bounded secondary metric and charge every stage.",
        "2. Balance or permute suspect labels consistently across paired variants, with frozen mappings and equal label representation. In the current expanded four-suspect cohort, S02 is correct in 17/32 worlds, so a constant S02 guess scores 53.125%.",
        "3. Separate requested evidence from evidence actually acquired, identifying evidence, contradictory answers, missing final calls, and per-call/cumulative resource stops. Select a clear token estimand and check native thinking/output limits before freezing it.",
        "4. Improve and independently review the controlled-English clue grammar, especially 'different ... value as suspect'. Version presentation changes without altering existing generated worlds. Add a small human solvability/interpretation check before test execution.",
        "5. Use balanced independent worlds, then allocate repeats to estimate sampling variance. Validate genuinely necessary cross-attribute reasoning rather than assuming the category label guarantees it. Freeze the next study only after reviewing this phase; the second $25 remains reserved.",
        "",
        "The detailed unexecuted proposal is in next-study-proposal.md. It does not change this phase's prompts, data, native tools or sampling settings.",
        "",
        "## Larger-study planning",
        "",
    ]
    for model, estimate in result["larger_study_cost_estimate"].items():
        amount = estimate["estimated_usd"]
        stats = describe([r for r in rows if r["model"] == model])
        seconds = stats["mean_seconds_among_finished"]
        projection = f"${amount:.2f}" if amount is not None else "unavailable"
        runtime = (
            f"{seconds * estimate['proposed_full_test_episodes'] / 3600:.1f} sequential hours"
            if seconds is not None
            else "unavailable"
        )
        lines.append(
            f"- **{model}**: {estimate['measured_episodes']} usage-complete measured episodes; naive projection {projection} for {estimate['proposed_full_test_episodes']:,} test episodes (744 cases × nine conditions × three repeats); measured-time projection {runtime}."
        )
    lines += [
        "",
        "These extrapolations are biased by development selection, incomplete condition coverage, resource failures, historical revisions and changing prices. Per-world mean episode cost intervals are in results.json. Conservative API-only all-output bounds at 32,768 reported tokens are $2,468.41 for Flash and $1,645.61 for Flash-Lite for the reference full study; probes and historical violations are additional. No full study is executed or authorized here.",
        "",
        "Qwen uses Apple M4 Pro, 24 GiB physical memory, Ollama 0.34.0, Q4_K_M digest `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`, and 32,768 configured context tokens. Its native compatibility probe passed and verified the loaded context and digest; loaded VRAM was approximately 6.11 GiB. Thinking is included in eval_count with no separate component. Hosted/local latency is descriptive, not a capability ranking.",
        "",
        "## Reproduction and verification",
        "",
        "The authoritative resume state is the local ledger.sqlite3; do not delete it or re-prepare a fresh budget. JSON, logs, checksum lists and figures are review artifacts. Export, evidence diagnostics and reporting make zero generation calls. The continuation source passed 151 tests, release/provenance checks over all 960 cases, package build and installed-wheel smoke verification. Additional post-hoc diagnostics checks are recorded in verification.json when present. Repository privacy and credential-pattern scanning are checked before final publication to the private Git branch. Licensing/publication and model selection remain pending.",
        "",
        "```sh",
        "uv run --locked python scripts/export_native_run.py studies/pilot-v0.3-reserved-recovery.json",
        "uv run --locked python scripts/evidence_diagnostics.py studies/pilot-v0.3-reserved-recovery.json",
        "uv run --locked python scripts/report_continuation.py studies/pilot-v0.3-reserved-recovery.json --final",
        "```",
        "",
        "Scientific figures use scripts/plot_continuation.py with a separate matplotlib runtime; no plotting dependency changes the frozen runner. See docs/pilot-continuation.md for native execution and budget controls.",
    ]
    (root / "docs" / "pilot-continuation-results.md").write_text(
        "\n".join(lines) + "\n"
    )
    print(
        json.dumps(
            {
                "snapshot": analysis["snapshot_kind"],
                "finished": sum(r["error"] not in MISSING for r in rows),
                "committed_usd": ledger["committed_usd"],
                "generation_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
