class ClueFormatter:
    """Convert structured clues to natural language"""

    @staticmethod
    def _attribute_label(attribute):
        return attribute.replace("_", " ")

    @staticmethod
    def _normalize_value(attribute, value):
        if attribute in {"weapon", "motive"}:
            return value.lower()
        return value

    @staticmethod
    def _indefinite_article(text):
        return "an" if text[:1].lower() in {"a", "e", "i", "o", "u"} else "a"

    @staticmethod
    def _direct_sentence(attribute, subject, value, negative=False):
        value_text = ClueFormatter._normalize_value(attribute, value)

        if attribute == "weapon":
            article = ClueFormatter._indefinite_article(value_text)
            verb = "was not carrying" if negative else "was carrying"
            return f"{subject} {verb} {article} {value_text}."

        if attribute == "location":
            verb = "was not in" if negative else "was in"
            return f"{subject} {verb} the {value_text}."

        if attribute == "motive":
            verb = "did not have" if negative else "had"
            return f"{subject} {verb} motive {value_text}." if negative else f"{subject}'s motive was {value_text}."

        if attribute == "time":
            verb = "was not seen at" if negative else "was seen at"
            return f"{subject} {verb} {value_text}."

        verb = "was not" if negative else "was"
        return f"{subject}'s {ClueFormatter._attribute_label(attribute)} {verb} {value_text}."

    @staticmethod
    def _crime_sentence(attribute, value, negative=False):
        value_text = ClueFormatter._normalize_value(attribute, value)

        if attribute == "weapon":
            article = ClueFormatter._indefinite_article(value_text)
            verb = "did not use" if negative else "used"
            return f"The murderer {verb} {article} {value_text}."

        if attribute == "location":
            verb = "did not take place in" if negative else "took place in"
            return f"The murder {verb} the {value_text}."

        if attribute == "motive":
            verb = "was not driven by" if negative else "was driven by"
            return f"The murderer {verb} {value_text}."

        if attribute == "time":
            verb = "did not happen at" if negative else "happened at"
            return f"The murder {verb} {value_text}."

        verb = "was not" if negative else "was"
        return f"The murderer's {ClueFormatter._attribute_label(attribute)} {verb} {value_text}."

    @staticmethod
    def _comparison_sentence(attribute, suspect, same=True):
        if attribute == "weapon":
            relation = "the same weapon as" if same else "a different weapon from"
            return f"The murderer used {relation} {suspect}."

        if attribute == "location":
            if same:
                return f"The murderer was in the same location as {suspect}."
            return f"The murderer was in a different location from {suspect}."

        if attribute == "motive":
            relation = "the same motive as" if same else "a different motive from"
            return f"The murderer had {relation} {suspect}."

        if attribute == "time":
            if same:
                return f"The murderer was seen at the same time as {suspect}."
            return f"The murderer was seen at a different time from {suspect}."

        relation = "the same" if same else "a different"
        return f"The murderer had {relation} {ClueFormatter._attribute_label(attribute)} as {suspect}."

    @staticmethod
    def _indirect_sentence(attr1, val1, attr2, val2, negative=False):
        val1_text = ClueFormatter._normalize_value(attr1, val1)
        val2_text = ClueFormatter._normalize_value(attr2, val2)

        if attr1 == "weapon":
            first = f"a suspect was carrying {ClueFormatter._indefinite_article(val1_text)} {val1_text}"
        elif attr1 == "location":
            first = f"a suspect was in the {val1_text}"
        elif attr1 == "motive":
            first = f"a suspect's motive was {val1_text}"
        elif attr1 == "time":
            first = f"a suspect was seen at {val1_text}"
        else:
            first = f"a suspect's {ClueFormatter._attribute_label(attr1)} was {val1_text}"

        if attr2 == "weapon":
            second = f"they were carrying {ClueFormatter._indefinite_article(val2_text)} {val2_text}"
        elif attr2 == "location":
            second = f"they were in the {val2_text}"
        elif attr2 == "motive":
            second = f"their motive was {val2_text}"
        elif attr2 == "time":
            second = f"they were seen at {val2_text}"
        else:
            second = f"their {ClueFormatter._attribute_label(attr2)} was {val2_text}"

        if negative:
            second = second.replace(" were ", " were not ", 1) if " were " in second else second.replace(" was ", " was not ", 1)

        return f"If {first}, {second}."

    @staticmethod
    def format(clue):
        if clue['type'] == 'unary_positive':
            return ClueFormatter._direct_sentence(
                clue['attribute'], clue['suspect'], clue['value']
            )

        elif clue['type'] == 'unary_negative':
            return ClueFormatter._direct_sentence(
                clue['attribute'], clue['suspect'], clue['value'], negative=True
            )

        elif clue['type'] == 'crime_positive':
            return ClueFormatter._crime_sentence(clue['attribute'], clue['value'])

        elif clue['type'] == 'crime_negative':
            return ClueFormatter._crime_sentence(
                clue['attribute'], clue['value'], negative=True
            )

        elif clue['type'] == 'crime_same_as':
            return ClueFormatter._comparison_sentence(
                clue['attribute'], clue['suspect'], same=True
            )

        elif clue['type'] == 'crime_different_from':
            return ClueFormatter._comparison_sentence(
                clue['attribute'], clue['suspect'], same=False
            )

        elif clue['type'] == 'indirect_positive':
            return ClueFormatter._indirect_sentence(
                clue['attr1'], clue['val1'], clue['attr2'], clue['val2']
            )

        elif clue['type'] == 'indirect_negative':
            return ClueFormatter._indirect_sentence(
                clue['attr1'], clue['val1'], clue['attr2'], clue['val2'], negative=True
            )

        return "Unknown clue type."
