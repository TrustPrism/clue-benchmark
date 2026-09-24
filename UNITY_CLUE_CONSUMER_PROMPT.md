# Unity/backend clue-consumer implementation prompt

Update the clue-consuming side of the game to manually import the generated
`generated_puzzle_states_1000.json` bank. Treat each `state` as a case and each
`clues.<bank_tier>.records[]` entry as an importable clue record.

Use `solver_fields` as the structured source of truth and `formatted_text` for
player-facing display. Preserve `case_id`, `clue_id`, and `clue_fact_id` in
game and telemetry data. When a player requests `easy`, `medium`, or `hard`,
select only from that bank tier; do not infer tier from `clue_complexity`.

Record the case ID, seed, bank tier, clue IDs, clue type, clue complexity,
direct-murderer-link flag, indirect flag, and whether the clue was marked
necessary for unique-murderer validation. Treat `unique_murderer` as the
solver guarantee: it means exactly one murderer is feasible, not that the
entire hidden world is unique. Cross-bank repeated facts are valid and are
identified by the same `clue_fact_id`; do not deduplicate records solely by
display text. This is a manual import/consumer change only—do not add an
automatic Unity synchronization layer.
