"""Controlled English preserves literal attribute and value labels exactly."""

import json

from .logic import clean


class ClueFormatter:
    @staticmethod
    def format(clue):
        c = clean(clue)

        def q(value):
            return json.dumps(value, ensure_ascii=False)

        t = c["type"]
        if t.startswith("unary_"):
            operator = "=" if t == "unary_positive" else "!="
            return f"Suspect {q(c['suspect'])} has {q(c['attribute'])} {operator} {q(c['value'])}."
        if t in ("crime_positive", "crime_negative"):
            operator = "=" if t == "crime_positive" else "!="
            return f"The murderer has {q(c['attribute'])} {operator} {q(c['value'])}."
        if t in ("crime_same_as", "crime_different_from"):
            relation = "the same" if t == "crime_same_as" else "a different"
            return f"The murderer has {relation} {q(c['attribute'])} value as suspect {q(c['suspect'])}."
        if t in ("suspect_same_as", "suspect_different_from"):
            relation = "the same" if t == "suspect_same_as" else "different"
            return f"Suspects {q(c['suspect'])} and {q(c['other_suspect'])} have {relation} {q(c['attribute'])} values."
        pair = f"{q(c['attr1'])} = {q(c['val1'])} and {q(c['attr2'])} = {q(c['val2'])}"
        if t == "indirect_positive":
            return f"At least one suspect has {pair}."
        return f"No suspect has both {pair}."
