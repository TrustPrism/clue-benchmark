"""Agent observations use an explicit allowlist; scoring is separate."""

import math
import random
from copy import deepcopy

from .clue_formatter import ClueFormatter
from .config import digest

RULES = (
    "Exactly one suspect is the murderer. Every suspect has exactly one value per attribute. "
    "Different suspects may share values. The crime's attributes equal the murderer's attributes. "
    "All clues are truthful. Only the murderer, not the full world, must be uniquely identifiable."
)
PROTOCOL_VERSION = "1.1"


def public_puzzle(case):
    return {
        "case_id": case["case_id"],
        "rules": RULES,
        "suspects": list(case["suspects"]),
        "domains": deepcopy(case["domains"]),
        "clues": [
            {"clue_id": f"c{i + 1:03d}", "text": ClueFormatter.format(c)}
            for i, c in enumerate(case["clues"])
        ],
    }


def topic(c):
    if c["type"].startswith("unary_"):
        return f"{c['suspect']} / {c['attribute']}"
    if c["type"].startswith("crime_"):
        return f"Crime / {c['attribute']}"
    return "Relationships / " + " + ".join(sorted((c["attr1"], c["attr2"])))


class Environment:
    def __init__(self, case, budget_fraction=1.0):
        if not math.isfinite(budget_fraction) or not 0 < budget_fraction <= 1:
            raise ValueError("budget_fraction must be in (0,1]")
        self._case = deepcopy(case)
        self._public = public_puzzle(case)
        self.budget = math.ceil(len(case["clues"]) * budget_fraction)
        self.max_requests = self.budget + max(2, self.budget)
        self._topics = {}
        for i, c in enumerate(case["clues"]):
            self._topics.setdefault(topic(c), []).append(i)
        labels = sorted(self._topics)
        random.Random(int(digest(case["clues"])[:16], 16)).shuffle(labels)
        self._queries = {f"q{i + 1:03d}": label for i, label in enumerate(labels)}
        self.reset()

    def reset(self):
        self.spent = 0
        self.requests = 0
        self.invalid_actions = 0
        self.answer = None
        self.done = False
        self._seen = []
        self._remaining = {
            q: list(self._topics[label]) for q, label in self._queries.items()
        }
        return self.observation()

    def observation(self):
        p = deepcopy(self._public)
        p["clues"] = [p["clues"][i] for i in self._seen]
        p.update(
            queries=[
                {"query_id": q, "topic": label, "remaining": len(self._remaining[q])}
                for q, label in self._queries.items()
            ],
            budget=self.budget,
            spent=self.spent,
            remaining_budget=self.budget - self.spent,
            max_requests=self.max_requests,
            requests=self.requests,
            remaining_requests=self.max_requests - self.requests,
            done=self.done,
        )
        return p

    def _request_status(self):
        return {
            "remaining_budget": self.budget - self.spent,
            "remaining_requests": self.max_requests - self.requests,
            "inventory": {q: len(items) for q, items in self._remaining.items()},
        }

    def request_clue(self, query_id):
        if self.done:
            return {"error": "episode_finished"}
        if self.spent >= self.budget:
            return {"error": "budget_exhausted", **self._request_status()}
        if self.requests >= self.max_requests:
            return {"error": "request_limit_exhausted", **self._request_status()}
        self.requests += 1
        if not isinstance(query_id, str) or query_id not in self._remaining:
            self.invalid_actions += 1
            return {"error": "unknown_query_id", **self._request_status()}
        if not self._remaining[query_id]:
            self.invalid_actions += 1
            return {"error": "topic_exhausted", **self._request_status()}
        self.spent += 1
        index = self._remaining[query_id].pop(0)
        self._seen.append(index)
        return {
            "clue": deepcopy(self._public["clues"][index]),
            **self._request_status(),
        }

    def submit_answer(self, suspect_id):
        if self.done:
            return {"error": "episode_finished"}
        self.done = True
        if isinstance(suspect_id, str) and suspect_id in self._case["suspects"]:
            self.answer = suspect_id
        else:
            self.invalid_actions += 1
        return {"accepted": self.answer is not None, "done": True}

    def score(self):
        return {
            "correct": int(self.answer == self._case["solution"]["murderer"]),
            "spent": self.spent,
            "requests": self.requests,
            "invalid_actions": self.invalid_actions,
        }
