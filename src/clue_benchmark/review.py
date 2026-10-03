"""Public review packets and strict, hash-bound independent-review collection."""

import random
from collections import defaultdict
from pathlib import Path

from .config import digest
from .environment import Environment
from .study import sha256


def presentation_hashes():
    root = Path(__file__).parent
    return {
        name: sha256(root / name) for name in ("environment.py", "clue_formatter.py")
    }


def prepare_review(cases, per_cell=2, topic_modes=("targeted", "attribute")):
    if type(per_cell) is not int or per_cell < 1 or not cases:
        raise ValueError("positive per-cell sample and nonempty cases required")
    if (
        len({c["case_id"] for c in cases}) != len(cases)
        or not topic_modes
        or len(set(topic_modes)) != len(topic_modes)
    ):
        raise ValueError("distinct case IDs and topic modes required")
    rng = random.Random(0)
    groups = defaultdict(list)
    for case in cases:
        groups[case.get("cell", f"n{len(case['suspects'])}")].append(case)
    items = []
    for cell, members in sorted(groups.items()):
        for case in rng.sample(
            sorted(members, key=lambda c: c["case_id"]), min(per_cell, len(members))
        ):
            for mode in topic_modes:
                env = Environment(case, topic_mode=mode)
                menu = env.observation()["queries"]
                items.append(
                    {
                        "review_id": digest([case["case_id"], mode]),
                        "cell": cell,
                        "case_id": case["case_id"],
                        "topic_mode": mode,
                        "deduction": env._public,
                        "queries": menu,
                        "response_examples": [
                            {
                                "query_id": q["query_id"],
                                "topic": q["topic"],
                                "response": Environment(
                                    case, topic_mode=mode
                                ).request_clue(q["query_id"]),
                            }
                            for q in menu
                        ],
                    }
                )
    packet = {
        "schema_version": "1.0",
        "status": "awaiting-independent-review",
        "sampling": f"Seed 0; up to {per_cell} cases per factorial cell; requested menu layouts.",
        "minimum_independent_reviewers_per_item": 2,
        "items": items,
        "source_case_ids": sorted(c["case_id"] for c in cases),
        "presentation_hashes": presentation_hashes(),
    }
    return {**packet, "packet_id": digest(packet)}


def review_template(packet):
    return {
        "packet_id": packet["packet_id"],
        "reviewer": {"id": "", "human": False, "independent": False},
        "completed_at": None,
        "reviews": [],
        "instructions": "For each review_id record wording_clear, topic_expectation_clear, optional suspect answer, and issues with severity blocking/minor. Attest human independent review only after performing it.",
    }


def collect_reviews(packet, responses, cases=None):
    if packet.get("packet_id") != digest(
        {k: v for k, v in packet.items() if k != "packet_id"}
    ):
        raise ValueError("review packet changed")
    if packet["presentation_hashes"] != presentation_hashes():
        raise ValueError("review presentation changed; prepare a new packet")
    minimum = packet["minimum_independent_reviewers_per_item"]
    if type(minimum) is not int or minimum < 2 or not packet["items"]:
        raise ValueError("nonempty packet and at least two reviewers per item required")
    items = {item["review_id"]: item for item in packet["items"]}
    if len(items) != len(packet["items"]):
        raise ValueError("duplicate packet item")
    coverage = defaultdict(set)
    reviewers, issues, answers = set(), [], []
    response_hashes = {}
    unchecked_answers = 0
    answer_key = {c["case_id"]: c["solution"]["murderer"] for c in cases or []}
    for response in responses:
        reviewer = response["reviewer"]
        identity = reviewer.get("id", "").strip()
        if response.get("packet_id") != packet["packet_id"]:
            raise ValueError("review is bound to a different packet")
        if (
            not identity
            or reviewer.get("human") is not True
            or reviewer.get("independent") is not True
            or not response.get("completed_at")
        ):
            raise ValueError("human independence and completion attestations required")
        if identity in reviewers:
            raise ValueError("duplicate reviewer identity")
        reviewers.add(identity)
        response_hashes[identity] = digest(response)
        seen = set()
        for review in response["reviews"]:
            key = review["review_id"]
            if key not in items or key in seen:
                raise ValueError("unknown or repeated review item")
            seen.add(key)
            if any(
                type(review.get(field)) is not bool
                for field in ("wording_clear", "topic_expectation_clear")
            ):
                raise ValueError("explicit wording and topic judgments required")
            coverage[key].add(identity)
            for issue in review.get("issues", []):
                if set(issue) - {"severity", "description"}:
                    raise ValueError("unexpected issue fields")
                if (
                    issue.get("severity") not in ("blocking", "minor")
                    or not issue.get("description", "").strip()
                ):
                    raise ValueError("issue requires severity and description")
                issues.append({"review_id": key, "reviewer": identity, **issue})
            if not review["wording_clear"] or not review["topic_expectation_clear"]:
                issues.append(
                    {
                        "review_id": key,
                        "reviewer": identity,
                        "severity": "blocking",
                        "description": "Reviewer did not approve wording or topic expectations.",
                    }
                )
            if review.get("answer") is not None and items[key]["case_id"] in answer_key:
                answers.append(
                    {
                        "review_id": key,
                        "reviewer": identity,
                        "correct": review["answer"]
                        == answer_key[items[key]["case_id"]],
                    }
                )
            elif review.get("answer") is not None:
                unchecked_answers += 1
    incomplete = [
        key
        for key in items
        if len(coverage[key]) < packet["minimum_independent_reviewers_per_item"]
    ]
    blocking = sum(issue["severity"] == "blocking" for issue in issues)
    report = {
        "packet_id": packet["packet_id"],
        "source_case_ids": packet["source_case_ids"],
        "presentation_hashes": packet["presentation_hashes"],
        "response_hashes": response_hashes,
        "items": len(items),
        "reviewers": sorted(reviewers),
        "incomplete_items": incomplete,
        "blocking_issues": blocking,
        "issues": issues,
        "submitted_answers": len(answers),
        "unchecked_answers": unchecked_answers,
        "incorrect_answers_for_adjudication": sum(not a["correct"] for a in answers),
        "status": "approved"
        if not incomplete
        and not blocking
        and not unchecked_answers
        and all(a["correct"] for a in answers)
        else "pending",
        "attestation_limits": "Checks validate reported coverage and judgments, not human identity. Maintainers must verify reviewer independence. A changed packet requires new signoff.",
    }
    return report
