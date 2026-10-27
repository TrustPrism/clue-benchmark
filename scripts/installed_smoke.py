"""Run using a noneditable installed package, outside the repository, offline."""

import importlib.util
import json
import socket
import subprocess
import sys
from pathlib import Path

from clue_benchmark import (
    evaluate_agent,
    export_public,
    generate_dataset,
    resolve_config,
    validate_dataset,
)
from clue_benchmark.replay import replay_example
from clue_benchmark.research_results import replay_nuisance
from clue_benchmark.results import replay_results


def forbidden(*args, **kwargs):
    raise AssertionError("offline smoke test attempted network")


socket.socket = forbidden
root = Path.cwd()
config = resolve_config(name="quickstart", output=str(root / "demo"))
assert generate_dataset(config)["complete"]
assert validate_dataset(root / "demo")["status"] == "verified"
export_public(root / "demo", root / "agent.jsonl", agent_id=0)
assert "solution" not in (root / "agent.jsonl").read_text()
assert evaluate_agent(root / "demo", lambda view: {"kind": "abstain"})["episodes"][0][
    "protocol_valid"
]
assert (
    replay_example("distributed-evidence", root / "replayed")["independent_worlds"] == 8
)
assert replay_results(root / "measured")["model_calls"] == 0
assert replay_nuisance(root / "nuisance")["combined"]["assigned"] == 144
subprocess.run(
    [sys.executable, "-m", "clue_benchmark", "--help"],
    check=True,
    stdout=subprocess.DEVNULL,
)
assert all(
    importlib.util.find_spec(name) is None
    for name in ("google.genai", "httpx", "matplotlib", "mkdocs")
    if importlib.util.find_spec(name.split(".")[0]) is not None
)
print(
    json.dumps(
        {
            "status": "passed",
            "python": sys.version.split()[0],
            "network": "blocked",
            "provider_extras": "absent",
            "installed_package": "noneditable",
            "worlds_replayed": 8,
        }
    )
)
