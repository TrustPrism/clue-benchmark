"""Install the built wheel into a clean environment and exercise it outside the checkout."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SMOKE = r"""
import json
from pathlib import Path
import clue_benchmark
from clue_benchmark import Config, generate, validate_case, public_puzzle
from clue_benchmark.environment import Environment
from clue_benchmark.evaluation import run_episode
assert Path(clue_benchmark.__file__).resolve().is_relative_to(Path(__import__('sys').prefix))
case = generate(Config(mutation_steps=0), 17)['case']
validate_case(case)
assert run_episode(case)['correct'] == 1
public = json.dumps(public_puzzle(case))
for field in ('solution', 'world', 'seed', 'config', 'solver_fields', 'diagnostics'):
    assert '"' + field + '"' not in public
import clue_benchmark.solver as solver_module
def forbidden(*args, **kwargs):
    raise AssertionError('evidence replay must not call a solver')
solver_module.Solver = forbidden
for mode in ('targeted', 'attribute'):
    env = Environment(case, topic_mode=mode)
    while env.spent < env.budget:
        query = next(q for q in env.observation()['queries'] if q['remaining'])
        assert 'clue' in env.request_clue(query['query_id'])
    assert len(env.observation()['clues']) == len(case['clues'])
    env.submit_answer(case['solution']['murderer'])
    assert env.score()['correct'] == 1
print('Installed package: generation, validation, scoring, both menus, and solver-free evidence replay passed.')
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    import tomllib

    release = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    wheels = list((root / "dist").glob(f"trustprism_clue_benchmark-{release}-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(
            "build exactly one wheel for the current software version first"
        )
    uv = shutil.which("uv") or str(root / ".venv/bin/uv")
    with tempfile.TemporaryDirectory(prefix="clue-wheel-") as tmp:
        env = Path(tmp) / "venv"
        subprocess.run([uv, "venv", "--python", sys.executable, str(env)], check=True)
        python = env / (
            "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
        )
        constraints = Path(tmp) / "locked-runtime.txt"
        subprocess.run(
            [
                uv,
                "export",
                "--locked",
                "--no-dev",
                "--no-emit-project",
                "--format",
                "requirements-txt",
                "--output-file",
                str(constraints),
            ],
            cwd=root,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                uv,
                "pip",
                "install",
                "--constraint",
                str(constraints),
                "--python",
                str(python),
                str(wheels[0]),
            ],
            check=True,
        )
        subprocess.run([str(python), "-I", "-c", SMOKE], cwd=tmp, check=True)
        subprocess.run(
            [
                str(python),
                "-I",
                "-m",
                "clue_benchmark",
                "generate",
                "--seed",
                "17",
                "--output",
                "case.json",
            ],
            cwd=tmp,
            check=True,
        )
        subprocess.run(
            [str(python), "-I", "-m", "clue_benchmark", "validate", "case.json"],
            cwd=tmp,
            check=True,
        )
    report = {
        "version": release,
        "wheel_sha256": hashlib.sha256(wheels[0].read_bytes()).hexdigest(),
        "lock_sha256": hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest(),
        "python": sys.version.split()[0],
        "status": "passed",
        "paid_calls": 0,
    }
    if args.output:
        Path(args.output).write_text(json.dumps(report, sort_keys=True) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
