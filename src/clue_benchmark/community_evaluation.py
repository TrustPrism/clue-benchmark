"""Frozen evaluation plans, native transports and durable no-retry reservations.

Live runs require new manifest-bound authorization. Preparation/dry runs use
neither credentials nor network connections.
"""

import heapq
import json
import math
import random
import sqlite3
import time
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

from .community_bundle import (
    file_hash,
    load_evaluator_cases,
    source_hashes,
    verify_manifest,
)
from .community_config import CommunityConfig
from .community_generation import iter_allocations, iter_nuisance, render_report, score
from .config import canonical, digest
from .dataset import atomic_json
from .native_adapters import normalize_response, request_payload
from .native_transport import NativeTransport
from .provider_events import safe_content
from .solver import Unresolved

CONDITIONS = ("complete", "independent", "sharing")
VENDORS = ("google", "openai", "anthropic", "ollama")


def graph_edges(kind, count):
    if kind not in ("star", "ring", "chain", "complete"):
        raise ValueError("unsupported graph")
    if kind == "star":
        pairs = [(0, i) for i in range(1, count)]
    elif kind == "chain":
        pairs = [(i, i + 1) for i in range(count - 1)]
    elif kind == "ring":
        pairs = [(i, (i + 1) % count) for i in range(count)] if count > 1 else []
    else:
        pairs = [(i, j) for i in range(count) for j in range(i + 1, count)]
    return sorted({(a, b) for i, j in pairs for a, b in ((i, j), (j, i)) if a != b})


def forward_evidence(
    case,
    part,
    graph="complete",
    rounds=3,
    max_reports_per_message=64,
    discussion=None,
    max_discussion_characters=1000,
):
    if (
        type(rounds) is not int
        or rounds < 0
        or type(max_reports_per_message) is not int
        or max_reports_per_message < 1
    ):
        raise ValueError("invalid communication limits")
    n = case["agent_count"]
    core = {r["report_id"]: r for r in case["reports"]}
    views = [
        {rid for rid, owners in part["core_allocation"].items() if a in owners}
        for a in range(n)
    ]
    edges, history, sent = graph_edges(graph, n), [], defaultdict(set)
    # Keep only the smallest IDs that can ever be transmitted in this finite
    # schedule. Nuisance records compete with useful clues by the same public
    # ordering; the policy cannot consult privileged relevance labels.
    capacity = max(1, max_reports_per_message * rounds)
    heaps = [[] for _ in range(n)]
    ownership = iter(iter_allocations(case, part))
    for _ in case["reports"]:
        next(ownership)
    for report in iter_nuisance(case):
        rid, owners = next(ownership)
        item = (-int(rid, 16), rid, report)
        for agent in owners:
            if len(heaps[agent]) < capacity:
                heapq.heappush(heaps[agent], item)
            elif item[0] > heaps[agent][0][0]:
                heapq.heapreplace(heaps[agent], item)
    for agent, heap in enumerate(heaps):
        for _, rid, report in heap:
            views[agent].add(rid)
            core[rid] = report
    for turn in range(rounds):
        next_views = [set(v) for v in views]
        for sender, recipient in edges:
            # The order is public identity order, never a privileged relevance rank.
            payload = sorted(views[sender] - sent[sender, recipient])[
                :max_reports_per_message
            ]
            sent[sender, recipient].update(payload)
            text = (discussion or {}).get((turn, sender), "")
            if not isinstance(text, str) or len(text) > max_discussion_characters:
                raise ValueError("discussion text exceeds declared allowance")
            if payload or text:
                history.append(
                    {
                        "round": turn,
                        "sender": sender,
                        "recipient": recipient,
                        "report_ids": payload,
                        "discussion": text,
                    }
                )
            next_views[recipient].update(payload)
        views = next_views
    return {
        "evidence": [[core[r] for r in sorted(v)] for v in views],
        "messages": history,
    }


def prepare_evaluation(
    root,
    models,
    *,
    conditions=CONDITIONS,
    repeats=1,
    graph="complete",
    rounds=3,
    max_reports_per_message=64,
    spending_ceiling_microdollars=0,
    max_requests=10000,
    forwarding_policy_identity="builtin-report-forwarding-1",
):
    manifest = verify_manifest(root)
    if (
        not isinstance(forwarding_policy_identity, str)
        or not forwarding_policy_identity
    ):
        raise ValueError("forwarding policy requires a stable identity")
    if not models:
        raise ValueError("user-supplied model configurations required")
    if (
        type(repeats) is not int
        or repeats < 1
        or not conditions
        or set(conditions) - set(CONDITIONS)
    ):
        raise ValueError("invalid evaluation conditions or repetitions")
    if (
        type(spending_ceiling_microdollars) is not int
        or spending_ceiling_microdollars < 0
    ):
        raise ValueError("nonnegative integer spending ceiling required")
    if type(max_requests) is not int or max_requests < 1:
        raise ValueError("positive request limit required")
    checked = []
    for model in models:
        allowed = {
            "id",
            "vendor",
            "model",
            "settings",
            "context_tokens",
            "input_microdollars_per_million_tokens",
            "output_microdollars_per_million_tokens",
            "identity",
            "tokenizer_identity",
        }
        if set(model) - allowed or not {
            "id",
            "vendor",
            "model",
            "settings",
            "context_tokens",
            "input_microdollars_per_million_tokens",
            "output_microdollars_per_million_tokens",
        } <= set(model):
            raise ValueError("incomplete or unknown model fields")
        if model["vendor"] not in VENDORS or any(
            not isinstance(model[k], str) or not model[k] for k in ("id", "model")
        ):
            raise ValueError("invalid model identity")
        settings = model["settings"]
        if not isinstance(settings, dict) or set(settings) - {
            "max_output_tokens",
            "temperature",
            "thinking_level",
            "reasoning_effort",
            "context_tokens",
            "seed",
        }:
            raise ValueError("unsupported provider settings")
        vendor_settings = {
            "google": {"max_output_tokens", "temperature", "thinking_level"},
            "openai": {"max_output_tokens", "reasoning_effort"},
            "anthropic": {"max_output_tokens"},
            "ollama": {"max_output_tokens", "context_tokens", "temperature", "seed"},
        }
        if set(settings) - vendor_settings[model["vendor"]]:
            raise ValueError("settings unsupported by the selected native translator")
        if "identity" in model and (
            not isinstance(model["identity"], str) or not model["identity"]
        ):
            raise ValueError("identity must be an exact expected returned model string")
        if (
            model["vendor"] == "ollama"
            and settings.get("context_tokens", 32768) != model["context_tokens"]
        ):
            raise ValueError("Ollama context setting and declared capacity must match")
        output = settings.get("max_output_tokens")
        if (
            type(output) is not int
            or output < 1
            or type(model["context_tokens"]) is not int
            or model["context_tokens"] <= output
        ):
            raise ValueError("invalid model context/output limits")
        for key in (
            "input_microdollars_per_million_tokens",
            "output_microdollars_per_million_tokens",
        ):
            if type(model[key]) is not int or model[key] < 0:
                raise ValueError("explicit nonnegative prices required")
        checked.append(deepcopy(model))
    if len({m["id"] for m in checked}) != len(checked):
        raise ValueError("duplicate model id")
    graph_edges(graph, manifest["config"]["distribution"]["agent_count"])
    if (
        type(rounds) is not int
        or rounds < 0
        or type(max_reports_per_message) is not int
        or max_reports_per_message < 1
    ):
        raise ValueError("invalid communication limits")
    plan = {
        "schema_version": "clue-community-evaluation-1",
        "bundle_files": manifest["files"],
        "bundle_manifest_hash": file_hash(Path(root) / "manifest.json"),
        "source_hashes": source_hashes(),
        "models": checked,
        "conditions": list(conditions),
        "repeats": repeats,
        "graph": graph,
        "rounds": rounds,
        "max_reports_per_message": max_reports_per_message,
        "forwarding_policy_identity": forwarding_policy_identity,
        "spending_ceiling_microdollars": spending_ceiling_microdollars,
        "max_requests": max_requests,
        "prompt": "Identify the responsible suspect from the supplied rules and reports. Submit answer(target) or abstain().",
        "tool_access": ["answer", "abstain"],
        "retries": 0,
        "external_inference": False,
        "tokenizer_identity": "per model if supplied; otherwise conservative serialized UTF-8 byte bound",
        "dataset_config": manifest["config"],
        "worlds": manifest["worlds"],
    }
    plan["plan_id"] = digest(plan)
    return plan


def check_plan(plan, root):
    body = {k: v for k, v in plan.items() if k != "plan_id"}
    if (
        plan.get("plan_id") != digest(body)
        or plan.get("schema_version") != "clue-community-evaluation-1"
    ):
        raise ValueError("evaluation plan identity mismatch")
    manifest = verify_manifest(root)
    if (
        manifest["files"] != plan["bundle_files"]
        or file_hash(Path(root) / "manifest.json") != plan["bundle_manifest_hash"]
        or source_hashes() != plan["source_hashes"]
        or plan["retries"] != 0
    ):
        raise ValueError("frozen evaluation inputs changed")


def _authorization(plan, value):
    required = {
        "schema_version",
        "plan_id",
        "approved_by",
        "approved_at",
        "spending_ceiling_microdollars",
        "max_requests",
    }
    if (
        not isinstance(value, dict)
        or set(value) != required
        or value["schema_version"] != "clue-community-authorization-1"
        or value["plan_id"] != plan["plan_id"]
        or not isinstance(value["approved_by"], str)
        or not value["approved_by"].strip()
        or not isinstance(value["approved_at"], str)
        or not value["approved_at"].strip()
        or value["spending_ceiling_microdollars"]
        != plan["spending_ceiling_microdollars"]
        or value["max_requests"] != plan["max_requests"]
    ):
        raise PermissionError(
            "new explicit community plan-bound authorization required"
        )
    return digest(value)


class Ledger:
    def __init__(self, path, plan):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.plan = plan
        self.db.executescript(
            "CREATE TABLE IF NOT EXISTS identity (id TEXT PRIMARY KEY);"
            "CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY,status TEXT,maximum INTEGER,actual INTEGER,result TEXT);"
        )
        ids = self.db.execute("SELECT id FROM identity").fetchall()
        if ids and ids[0]["id"] != plan["plan_id"]:
            raise ValueError("ledger belongs to another frozen plan")
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO identity VALUES (?)", (plan["plan_id"],)
            )

    def reserve(self, ident, maximum):
        self.db.execute("BEGIN IMMEDIATE")
        with self.db:
            if self.db.execute(
                "SELECT 1 FROM requests WHERE id=?", (ident,)
            ).fetchone():
                return False
            held = self.db.execute(
                "SELECT 1 FROM requests WHERE status IN ('dispatched','held_unknown','resource_breach','identity_drift') LIMIT 1"
            ).fetchone()
            if held:
                raise PermissionError(
                    "unresolved dispatch/usage or resource breach blocks new calls"
                )
            count, cost = self.db.execute(
                "SELECT COUNT(*),COALESCE(SUM(COALESCE(actual,maximum)),0) FROM requests WHERE status != 'preflight_failed'"
            ).fetchone()
            if (
                count >= self.plan["max_requests"]
                or cost + maximum > self.plan["spending_ceiling_microdollars"]
            ):
                raise PermissionError("community request or spending limit reached")
            self.db.execute(
                "INSERT INTO requests VALUES (?,'dispatched',?,NULL,NULL)",
                (ident, maximum),
            )
        return True

    def record(self, ident, status, result, actual=None):
        with self.db:
            self.db.execute(
                "UPDATE requests SET status=?,actual=?,result=? WHERE id=?",
                (status, actual, canonical(safe_content(result)), ident),
            )

    def rows(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM requests ORDER BY id")]

    def close(self):
        self.db.close()


class DispatchPermit:
    def __init__(self, ledger, plan, model, request_id, payload, authorization):
        self.ledger, self.plan, self.model, self.request_id, self.payload_hash = (
            ledger,
            plan,
            model,
            request_id,
            digest(payload),
        )
        self.authorization_hash = _authorization(plan, authorization)
        self.used = False

    def check(self, vendor, payload):
        row = self.ledger.db.execute(
            "SELECT status FROM requests WHERE id=?", (self.request_id,)
        ).fetchone()
        if (
            self.used
            or not row
            or row["status"] != "dispatched"
            or vendor != self.model["vendor"]
            or digest(payload) != self.payload_hash
        ):
            raise PermissionError("invalid or reused community dispatch permit")
        self.used = True


def _custom_forwarding(case, part, plan, policy, presentation):
    # The adapter receives only agent-safe content and ownership, never labels.
    headers = {
        k: case[k]
        for k in (
            "case_id",
            "world_id",
            "suspects",
            "domains",
            "display_names",
            "rules",
            "assignment_mode",
            "corruption_allowance",
            "agent_count",
        )
    }
    records = (
        render_report(r, case, presentation)
        for group in (case["reports"], iter_nuisance(case))
        for r in group
    )
    result = policy(
        headers,
        records,
        iter_allocations(case, part),
        {
            "graph": plan["graph"],
            "rounds": plan["rounds"],
            "max_reports_per_message": plan["max_reports_per_message"],
            "max_discussion_characters": 1000,
        },
    )
    n = case["agent_count"]
    views = [set() for _ in range(n)]
    for rid, owners in iter_allocations(case, part):
        for agent in owners:
            views[agent].add(rid)
    messages = result["messages"]
    edges = set(graph_edges(plan["graph"], n))
    slots = set()
    for message in messages:
        turn, sender, recipient = (message[k] for k in ("round", "sender", "recipient"))
        if (
            type(turn) is not int
            or not 0 <= turn < plan["rounds"]
            or (sender, recipient) not in edges
            or (turn, sender, recipient) in slots
        ):
            raise ValueError("adapter message violates communication schedule")
        slots.add((turn, sender, recipient))
        ids, discussion = message["report_ids"], message.get("discussion", "")
        if (
            len(ids) > plan["max_reports_per_message"]
            or len(set(ids)) != len(ids)
            or not isinstance(discussion, str)
            or len(discussion) > 1000
        ):
            raise ValueError("adapter message exceeds declared limits")
    for turn in range(plan["rounds"]):
        next_views = [set(v) for v in views]
        for message in messages:
            if message["round"] == turn:
                if not set(message["report_ids"]) <= views[message["sender"]]:
                    raise ValueError("adapter forwards unavailable report")
                next_views[message["recipient"]].update(message["report_ids"])
        views = next_views
    if len(result["evidence"]) != n or any(
        not set(ids) <= views[a] for a, ids in enumerate(result["evidence"])
    ):
        raise ValueError("adapter supplies undelivered evidence")
    return result


def _observations(case, plan, condition, forwarding_policy=None):
    part = case["saved_certificate"]["partition"]
    cfg = CommunityConfig.from_dict(case["config"])
    rendered = {
        r["report_id"]: render_report(r, case, cfg.presentation)
        for r in case["reports"]
    }
    if condition == "complete":
        groups = [list(rendered)]
        messages = []
    elif condition == "independent":
        groups = [
            [rid for rid, owners in part["core_allocation"].items() if a in owners]
            for a in range(case["agent_count"])
        ]
        messages = []
    else:
        if forwarding_policy is None:
            forwarding = forward_evidence(
                case,
                part,
                plan["graph"],
                plan["rounds"],
                plan["max_reports_per_message"],
            )
            selected = {r["report_id"] for r in forwarding["evidence"][0]}
        else:
            forwarding = _custom_forwarding(
                case, part, plan, forwarding_policy, cfg.presentation
            )
            selected = set(forwarding["evidence"][0])
        groups = [sorted(selected & set(rendered))]
        forwarded_noise = selected - set(rendered)
        messages = forwarding["messages"]
    max_bytes = max(m["context_tokens"] for m in plan["models"])
    noise_views = [[] for _ in groups]
    bytes_used = [0 for _ in groups]
    allocations = iter(iter_allocations(case, part))
    for _ in case["reports"]:
        next(allocations)
    for report in iter_nuisance(case):
        _, owners = next(allocations)
        public = render_report(report, case, cfg.presentation)
        # Large corpora fail preflight, never silently truncate to fit.
        for a in range(len(groups)):
            accessible = condition == "complete" or (
                a in owners
                if condition == "independent"
                else 0 in owners or report["report_id"] in forwarded_noise
            )
            if accessible:
                bytes_used[a] += len(canonical(public).encode())
                if bytes_used[a] <= max_bytes:
                    noise_views[a].append(public)
    for agent, ids in enumerate(groups):
        overflow = bytes_used[agent] > max_bytes
        observation = {
            "instruction": plan["prompt"],
            "suspects": case["suspects"],
            "domains": case["domains"],
            "display_names": case["display_names"],
            "rules": case["rules"],
            "assignment_mode": case["assignment_mode"],
            "corruption_allowance": case["corruption_allowance"],
            "padding": case["padding"],
            "reports": [rendered[rid] for rid in ids] + noise_views[agent],
            "discussion": [
                m.get("discussion", "")
                for m in messages
                if m["recipient"] == agent and m.get("discussion")
            ],
        }
        yield agent, observation, [rendered[rid] for rid in ids], messages, overflow


def _cost(model, input_tokens, output_tokens):
    return math.ceil(
        (
            input_tokens * model["input_microdollars_per_million_tokens"]
            + output_tokens * model["output_microdollars_per_million_tokens"]
        )
        / 1000000
    )


def run_evaluation(
    plan,
    root,
    output_directory,
    *,
    dry_run=True,
    authorization=None,
    transports=None,
    forwarding_policy=None,
):
    check_plan(plan, root)
    identity = getattr(
        forwarding_policy,
        "identity",
        "builtin-report-forwarding-1" if forwarding_policy is None else None,
    )
    if identity != plan["forwarding_policy_identity"]:
        raise ValueError("forwarding adapter identity differs from frozen plan")
    if not dry_run:
        _authorization(plan, authorization)
    results, preflights = [], []
    ledger = (
        None if dry_run else Ledger(Path(output_directory) / "requests.sqlite", plan)
    )
    stopped = None
    accounting_rows = []
    try:
        for case in load_evaluator_cases(root):
            for condition in plan["conditions"]:
                for agent, observation, evidence, messages, overflow in _observations(
                    case, plan, condition, forwarding_policy
                ):
                    for repeat in range(plan["repeats"]):
                        for model in plan["models"]:
                            ident = digest(
                                [
                                    plan["plan_id"],
                                    case["case_id"],
                                    condition,
                                    agent,
                                    repeat,
                                    model["id"],
                                ]
                            )
                            payload = request_payload(
                                model["vendor"],
                                model["model"],
                                observation,
                                "answering",
                                model["settings"],
                            )
                            input_bound = len(canonical(payload).encode()) + 2048
                            output_bound = model["settings"]["max_output_tokens"]
                            fits = (
                                not overflow
                                and input_bound + output_bound
                                <= model["context_tokens"]
                            )
                            maximum = _cost(model, input_bound, output_bound)
                            base = {
                                "request_id": ident,
                                "world_id": case["world_id"],
                                "case_id": case["case_id"],
                                "model": model["id"],
                                "condition": condition,
                                "agent": agent,
                                "repeat": repeat,
                                "messages": len(messages),
                                "forwarded_reports": sum(
                                    len(m["report_ids"]) for m in messages
                                ),
                                "input_token_upper_bound": input_bound,
                                "maximum_microdollars": maximum,
                                "context_fits": fits,
                            }
                            if dry_run:
                                preflights.append(base)
                                continue
                            existing = ledger.db.execute(
                                "SELECT status,result FROM requests WHERE id=?",
                                (ident,),
                            ).fetchone()
                            if existing:
                                if existing["result"]:
                                    results.append(json.loads(existing["result"]))
                                    continue
                                stopped = (
                                    "interrupted_dispatch_retains_full_reservation"
                                )
                                raise PermissionError(stopped)
                            if not fits:
                                failure = {
                                    **base,
                                    "transport": "context_overflow",
                                    "correct": False,
                                    "supported": False,
                                    "protocol_valid": False,
                                    "dispatched": False,
                                }
                                # Persist preflight failures too, without a paid reservation.
                                with ledger.db:
                                    ledger.db.execute(
                                        "INSERT INTO requests VALUES (?,'preflight_failed',0,0,?)",
                                        (ident, canonical(failure)),
                                    )
                                results.append(failure)
                                continue
                            ledger.reserve(ident, maximum)
                            permit = DispatchPermit(
                                ledger, plan, model, ident, payload, authorization
                            )
                            transport = (transports or {}).get(model["id"])
                            started = time.monotonic()
                            try:
                                if transport is None:
                                    native = NativeTransport(model["vendor"])
                                    raw = native.call_authorized(payload, permit)
                                else:
                                    permit.check(model["vendor"], payload)
                                    raw = transport(payload)
                                response = normalize_response(model["vendor"], raw)
                                counters = response["receipt"]["counters"]
                                inp, candidate, thinking, total = (
                                    counters[k]
                                    for k in (
                                        "prompt_token_count",
                                        "candidates_token_count",
                                        "thoughts_token_count",
                                        "total_token_count",
                                    )
                                )
                                usage_known = (
                                    not response["receipt"]["invalid_counters"]
                                    and all(
                                        type(v) is int and v >= 0
                                        for v in (inp, candidate, thinking, total)
                                    )
                                    and total == inp + candidate + thinking
                                )
                                common = {
                                    **base,
                                    "transport": response["transport"],
                                    "returned_model": response["returned_model"],
                                    "wall_seconds": time.monotonic() - started,
                                    "calls": 1,
                                    "dispatched": True,
                                    "input_tokens": inp,
                                    "output_tokens": None
                                    if candidate is None or thinking is None
                                    else candidate + thinking,
                                    "thinking_tokens": thinking,
                                    "receipt": response["receipt"],
                                    "correct": False,
                                    "supported": False,
                                    "protocol_valid": False,
                                }
                                if not usage_known:
                                    ledger.record(ident, "held_unknown", common)
                                    results.append(common)
                                    raise PermissionError(
                                        "unknown usage retains full reservation"
                                    )
                                actual = _cost(model, inp, candidate + thinking)
                                if (
                                    inp > input_bound
                                    or candidate + thinking > output_bound
                                    or actual > maximum
                                ):
                                    ledger.record(
                                        ident, "resource_breach", common, actual
                                    )
                                    results.append(common)
                                    raise PermissionError(
                                        "provider exceeded reserved resources"
                                    )
                                if (
                                    model.get("identity") is not None
                                    and response["returned_model"] != model["identity"]
                                ):
                                    ledger.record(
                                        ident, "identity_drift", common, actual
                                    )
                                    results.append(common)
                                    raise PermissionError(
                                        "returned model identity differs from frozen identity"
                                    )
                                calls = response["calls"]
                                answer = None
                                if response["transport"] == "ok" and len(calls) == 1:
                                    call = calls[0]
                                    if (
                                        call["name"] == "abstain"
                                        and call["arguments"] == {}
                                    ):
                                        answer = {"kind": "abstain"}
                                    elif (
                                        call["name"] == "answer"
                                        and isinstance(call["arguments"], dict)
                                        and set(call["arguments"]) == {"target"}
                                    ):
                                        answer = {
                                            "kind": "answer",
                                            "target": call["arguments"]["target"],
                                        }
                                try:
                                    grades = score(case, answer, evidence)
                                except Unresolved:
                                    grades = {
                                        "correct": False,
                                        "supported": False,
                                        "protocol_valid": False,
                                        "evaluator_status": "unknown",
                                    }
                                completed = {
                                    **common,
                                    **grades,
                                    "answer": answer,
                                    "actual_microdollars": actual,
                                }
                                ledger.record(ident, "settled", completed, actual)
                                results.append(completed)
                            except PermissionError:
                                raise
                            except Exception as exc:
                                failure = {
                                    **base,
                                    "transport": type(exc).__name__,
                                    "wall_seconds": time.monotonic() - started,
                                    "dispatched": True,
                                    "calls": 1,
                                    "correct": False,
                                    "supported": False,
                                    "protocol_valid": False,
                                }
                                ledger.record(ident, "held_unknown", failure)
                                results.append(failure)
                                raise PermissionError(
                                    "transport failure retains full reservation"
                                ) from None
    except PermissionError as exc:
        stopped = str(exc)
    finally:
        if ledger:
            accounting_rows = ledger.rows()
            ledger.close()
    if dry_run:
        return {
            "plan_id": plan["plan_id"],
            "dry_run": True,
            "network_calls": 0,
            "requests": preflights,
            "expected_requests": len(preflights),
            "maximum_microdollars": sum(
                r["maximum_microdollars"] for r in preflights if r["context_fits"]
            ),
        }
    if stopped is not None:
        planned = run_evaluation(
            plan,
            root,
            output_directory,
            dry_run=True,
            forwarding_policy=forwarding_policy,
        )["requests"]
        included = {e["request_id"] for e in results}
        results.extend(
            {
                **e,
                "transport": "not_attempted_administrative",
                "dispatched": False,
                "correct": False,
                "supported": False,
                "protocol_valid": False,
            }
            for e in planned
            if e["request_id"] not in included
        )
    summary = summarize(results)
    report = {
        "plan_id": plan["plan_id"],
        "complete": stopped is None,
        "stopped_reason": stopped,
        "episodes": results,
        "summary": summary,
        "all_assigned_failures_retained": True,
        "accounting": {
            "settled_microdollars": sum(r["actual"] or 0 for r in accounting_rows),
            "held_microdollars": sum(
                r["maximum"] for r in accounting_rows if r["actual"] is None
            ),
            "unknown_receipts": sum(
                r["status"] in ("dispatched", "held_unknown") for r in accounting_rows
            ),
        },
    }
    atomic_json(Path(output_directory) / "results.json", report)
    return report


def summarize(episodes):
    """World-clustered means and deterministic percentile bootstrap intervals."""
    groups = defaultdict(lambda: defaultdict(list))
    for e in episodes:
        groups[e["model"], e["condition"]][e["world_id"]].append(e)
    result = []
    for (model, condition), worlds in sorted(groups.items()):
        means = [
            sum(bool(e.get("supported")) for e in es) / len(es)
            for es in worlds.values()
        ]
        rng = random.Random(0)
        samples = sorted(
            sum(rng.choice(means) for _ in means) / len(means) for _ in range(2000)
        )
        all_episodes = [e for es in worlds.values() for e in es]
        result.append(
            {
                "model": model,
                "condition": condition,
                "worlds": len(worlds),
                "episodes": len(all_episodes),
                "supported_accuracy": sum(means) / len(means),
                "world_cluster_bootstrap_95_interval": [samples[49], samples[1949]],
                "correct_accuracy": sum(
                    sum(bool(e.get("correct")) for e in es) / len(es)
                    for es in worlds.values()
                )
                / len(worlds),
                "protocol_failures": sum(
                    not e.get("protocol_valid", False) for e in all_episodes
                ),
                "abstentions": sum(bool(e.get("abstained")) for e in all_episodes),
                "actual_microdollars": sum(
                    e.get("actual_microdollars", 0) for e in all_episodes
                ),
                "calls": sum(e.get("calls", 0) for e in all_episodes),
                "input_tokens": sum(e.get("input_tokens") or 0 for e in all_episodes),
                "output_tokens": sum(e.get("output_tokens") or 0 for e in all_episodes),
                "unknown_usage_episodes": sum(
                    e.get("dispatched", False) and e.get("input_tokens") is None
                    for e in all_episodes
                ),
                "interval_scope": "descriptive world bootstrap; single-world intervals are uninformative",
            }
        )
    return result
