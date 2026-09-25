from clue_benchmark import Config, Environment, generate

result = generate(Config(), seed=42)
if result["status"] != "ok":
    raise RuntimeError(result["diagnostics"])
env = Environment(result["case"], budget_fraction=0.5)
print(env.reset())
print(env.request_clue(env.observation()["queries"][0]["query_id"]))
# Agent receives observations only; the evaluator owns env.score().
print(env.submit_answer("S01"))
print(env.score())
