import json
from pathlib import Path
import unittest


class RepresentativeOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).parents[1] / "generated_puzzle_states_study_v24.json"
        if not path.exists():
            raise unittest.SkipTest("representative output has not been generated")
        cls.output = json.loads(path.read_text(encoding="utf-8"))

    def test_import_ready_schema_and_difficulty_banks(self):
        self.assertEqual(self.output["version"], 24)
        state = self.output["states"][0]
        self.assertTrue(state["metadata"]["manual_import_ready"])
        self.assertEqual(set(state["clues"]), {"easy", "medium", "hard"})

        expected_counts = {"easy": 5, "medium": 7, "hard": 8}
        for tier, bank in state["clues"].items():
            self.assertEqual(bank["count"], expected_counts[tier])
            self.assertEqual(len(bank["records"]), bank["count"])
            self.assertTrue(bank["validation"]["truthful_for_generated_world"])
            self.assertTrue(bank["validation"]["solver_compatible"])
            self.assertTrue(bank["validation"]["unique_murderer"])
            for record in bank["records"]:
                self.assertEqual(record["bank_tier"], tier)
                self.assertIn(record["clue_complexity"], {
                    "easy", "medium", "hard", "very_hard"
                })
                self.assertTrue(record["formatted_text"])
                self.assertTrue(record["clue_id"])
                self.assertTrue(record["clue_fact_id"])

    def test_generation_time_and_duplicate_diagnostics_are_present(self):
        diagnostic = next(
            item for item in self.output["diagnostics"]
            if item["status"] == "ok"
        )
        self.assertGreater(diagnostic["generation_duration_seconds"], 0)
        self.assertLess(diagnostic["generation_duration_seconds"], 120)
        self.assertIn("clue_complexity_counts", diagnostic)
        self.assertIn("duplicate_counts", diagnostic)
        self.assertIn("across_banks", diagnostic["duplicate_counts"])


if __name__ == "__main__":
    unittest.main()
