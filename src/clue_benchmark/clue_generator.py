import random

from .clue_metadata import clue_fact_id


class ClueGenerator:
    def __init__(self, world, murderer, domains):
        self.world = world
        self.murderer = murderer
        self.domains = domains
        self.clue_pool = []
        self.attributes = list(domains.keys())

    def build_clue_pool(self, rng=None):
        """Generate all possible truthful clues"""
        rng = rng or random
        self.clue_pool = []
        self._generate_direct_clues()
        self._generate_complex_clues()
        self._dedupe_clue_pool()
        rng.shuffle(self.clue_pool)
        return len(self.clue_pool)

    def _generate_direct_clues(self):
        # Unary positive/negative
        for suspect in self.world:
            for attr, value in self.world[suspect].items():
                # Positive
                self.clue_pool.append(
                    {
                        "type": "unary_positive",
                        "suspect": suspect,
                        "attribute": attr,
                        "value": value,
                        "difficulty": "easy",
                    }
                )
                # Negative (for all other values)
                for other_val in self.domains[attr]:
                    if other_val != value:
                        self.clue_pool.append(
                            {
                                "type": "unary_negative",
                                "suspect": suspect,
                                "attribute": attr,
                                "value": other_val,
                                "difficulty": "medium",
                            }
                        )

        # Crime attribute clues
        crime_tuple = self.world[self.murderer]
        for attr, value in crime_tuple.items():
            self.clue_pool.append(
                {
                    "type": "crime_positive",
                    "attribute": attr,
                    "value": value,
                    "difficulty": "easy",
                }
            )
            for other_val in self.domains[attr]:
                if other_val != value:
                    self.clue_pool.append(
                        {
                            "type": "crime_negative",
                            "attribute": attr,
                            "value": other_val,
                            "difficulty": "hard",
                        }
                    )

            for suspect, attrs in self.world.items():
                if suspect == self.murderer:
                    continue

                relation_type = (
                    "crime_same_as" if attrs[attr] == value else "crime_different_from"
                )
                self.clue_pool.append(
                    {
                        "type": relation_type,
                        "suspect": suspect,
                        "attribute": attr,
                        "difficulty": "hard",
                    }
                )

    def _generate_complex_clues(self):
        # Indirect positive: ∃s: X_s,A=v ∧ X_s,B=w
        for suspect in self.world:
            for attr1 in self.attributes:
                for attr2 in self.attributes:
                    if attr1 != attr2:
                        v1 = self.world[suspect][attr1]
                        v2 = self.world[suspect][attr2]
                        self.clue_pool.append(
                            {
                                "type": "indirect_positive",
                                "attr1": attr1,
                                "val1": v1,
                                "attr2": attr2,
                                "val2": v2,
                                "difficulty": "hard",
                            }
                        )

        # Indirect negative: ∀s: X_s,A=v ⇒ X_s,B≠w
        # (Check if this is actually true in world)
        for attr1 in self.attributes:
            for val1 in self.domains[attr1]:
                if not self._antecedent_exists(attr1, val1):
                    continue
                for attr2 in self.attributes:
                    if attr1 != attr2:
                        for val2 in self.domains[attr2]:
                            if self._is_negative_rule_true(attr1, val1, attr2, val2):
                                self.clue_pool.append(
                                    {
                                        "type": "indirect_negative",
                                        "attr1": attr1,
                                        "val1": val1,
                                        "attr2": attr2,
                                        "val2": val2,
                                        "difficulty": "very_hard",
                                    }
                                )

    def _is_negative_rule_true(self, attr1, val1, attr2, val2):
        """Check if ∀s: X_s,attr1=val1 ⇒ X_s,attr2≠val2"""
        for suspect, attrs in self.world.items():
            if attrs[attr1] == val1 and attrs[attr2] == val2:
                return False
        return True

    def _antecedent_exists(self, attr, value):
        """Avoid vacuous implication clues with no supporting suspect."""
        for attrs in self.world.values():
            if attrs[attr] == value:
                return True
        return False

    def _dedupe_clue_pool(self):
        """Remove exact duplicate clues that arise from repeated world patterns."""
        seen = set()
        deduped = []

        for clue in self.clue_pool:
            key = clue_fact_id(clue)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(clue)

        self.clue_pool = deduped
