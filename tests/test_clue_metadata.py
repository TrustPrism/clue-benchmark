import unittest

from clue_formatter import ClueFormatter
from clue_generator import ClueGenerator
from clue_metadata import (
    case_id_for_seed,
    clue_fact_id,
    clue_id_for,
    decorate_clue,
    duplicate_stats,
)
from clue_validation import clue_is_true, validate_bank, validate_clue_record
from csp_solver import MysteryCSPSolver


DOMAINS = {
    "weapon": ["Wrench", "Rope"],
    "location": ["Study", "Kitchen"],
}
WORLD = {
    "Alice": {"weapon": "Wrench", "location": "Study"},
    "Bob": {"weapon": "Rope", "location": "Kitchen"},
}


class ClueMetadataTests(unittest.TestCase):
    def test_ids_are_deterministic_and_fact_ids_ignore_bank(self):
        clue = {
            "type": "crime_positive",
            "attribute": "weapon",
            "value": "Wrench",
            "difficulty": "easy",
        }
        case_id = case_id_for_seed(7)
        fact_id = clue_fact_id(clue)
        self.assertEqual(fact_id, clue_fact_id(dict(clue)))
        self.assertEqual(
            clue_id_for(case_id, "easy", fact_id),
            clue_id_for(case_id, "easy", fact_id),
        )
        self.assertNotEqual(
            clue_id_for(case_id, "easy", fact_id),
            clue_id_for(case_id, "hard", fact_id),
        )

    def test_truth_and_solver_compatibility_for_entire_pool(self):
        generator = ClueGenerator(WORLD, "Alice", DOMAINS)
        generator.build_clue_pool()
        solver = MysteryCSPSolver(
            list(WORLD), DOMAINS, WORLD, "Alice"
        )
        for clue in generator.clue_pool:
            self.assertTrue(clue_is_true(clue, WORLD, "Alice"), clue)
            self.assertTrue(solver.is_true_murderer_feasible([clue]), clue)

    def test_records_validate_and_keep_structured_fields(self):
        raw = {
            "type": "crime_positive",
            "attribute": "weapon",
            "value": "Wrench",
            "difficulty": "easy",
        }
        solver = MysteryCSPSolver(
            list(WORLD), DOMAINS, WORLD, "Alice"
        )
        record = decorate_clue(
            raw,
            case_id_for_seed(7),
            "easy",
            ClueFormatter.format(raw),
        )
        valid, reason = validate_clue_record(record, WORLD, "Alice", solver)
        self.assertTrue(valid, reason)
        self.assertEqual(record["solver_fields"]["type"], "crime_positive")
        self.assertEqual(record["formatted_text"], "The murderer used a wrench.")

    def test_duplicate_statistics_are_explicit(self):
        records = [
            {"clue_fact_id": "fact-a", "formatted_text": "same"},
            {"clue_fact_id": "fact-a", "formatted_text": "same"},
            {"clue_fact_id": "fact-b", "formatted_text": "same"},
        ]
        stats = duplicate_stats(records)
        self.assertEqual(stats["exact_duplicate_fact_count"], 1)
        self.assertEqual(stats["exact_duplicate_text_count"], 2)


if __name__ == "__main__":
    unittest.main()
