from ortools.sat.python import cp_model


class MysteryCSPSolver:
    def __init__(self, suspects, domains, true_world, true_murderer):
        self.suspects = suspects
        self.domains = domains
        self.true_world = true_world
        self.true_murderer = true_murderer
        self._feasible_cache = {}
        self._count_cache = {}
        self._unique_cache = {}

    def is_unique(self, clues):
        """Check if exactly 1 murderer is feasible"""
        key = self._clues_key(clues)
        if key not in self._unique_cache:
            self._unique_cache[key] = self.count_feasible_murderers(clues) == 1
        return self._unique_cache[key]

    def count_feasible_murderers(self, clues):
        """Count how many suspects could be the murderer"""
        key = self._clues_key(clues)
        if key in self._count_cache:
            return self._count_cache[key]

        feasible_count = 0
        for candidate in self.suspects:
            if self._is_feasible_murderer(candidate, clues):
                feasible_count += 1
        self._count_cache[key] = feasible_count
        return feasible_count

    def _is_feasible_murderer(self, candidate, clues):
        """
        Check if candidate can be murderer given clues
        Formulate as CP-SAT problem
        """
        key = (candidate, self._clues_key(clues))
        if key in self._feasible_cache:
            return self._feasible_cache[key]

        model = cp_model.CpModel()

        # Decision variables: δ_s,A,v
        delta = {}
        for s in self.suspects:
            delta[s] = {}
            for attr in self.domains:
                delta[s][attr] = {}
                for val in self.domains[attr]:
                    delta[s][attr][val] = model.NewBoolVar(f'd_{s}_{attr}_{val}')

        # Constraint: each suspect has exactly one value per attribute
        for s in self.suspects:
            for attr in self.domains:
                model.Add(sum(delta[s][attr][v] for v in self.domains[attr]) == 1)

        # Crime variables linked to candidate murderer
        crime = {}
        for attr in self.domains:
            crime[attr] = {}
            for val in self.domains[attr]:
                crime[attr][val] = delta[candidate][attr][val]

        # Encode all clues as constraints
        for clue in clues:
            self._encode_clue(model, clue, delta, crime)

        # Solve
        solver = cp_model.CpSolver()
        status = solver.Solve(model)

        is_feasible = status == cp_model.FEASIBLE or status == cp_model.OPTIMAL
        self._feasible_cache[key] = is_feasible
        return is_feasible

    def _clues_key(self, clues):
        """Canonical hashable key for a clue set."""
        return tuple(sorted(self._clue_key(clue) for clue in clues))

    def _clue_key(self, clue):
        return tuple(sorted(clue.items()))

    def _encode_clue(self, model, clue, delta, crime):
        """Translate clue to CP-SAT constraints"""
        if clue['type'] == 'unary_positive':
            # X_s,A = v
            s, a, v = clue['suspect'], clue['attribute'], clue['value']
            model.Add(delta[s][a][v] == 1)

        elif clue['type'] == 'unary_negative':
            # X_s,A ≠ v
            s, a, v = clue['suspect'], clue['attribute'], clue['value']
            model.Add(delta[s][a][v] == 0)

        elif clue['type'] == 'crime_positive':
            # C_A = v
            a, v = clue['attribute'], clue['value']
            model.Add(crime[a][v] == 1)

        elif clue['type'] == 'crime_negative':
            # C_A != v
            a, v = clue['attribute'], clue['value']
            model.Add(crime[a][v] == 0)

        elif clue['type'] == 'crime_same_as':
            # C_A = X_s,A
            s, a = clue['suspect'], clue['attribute']
            for v in self.domains[a]:
                model.Add(crime[a][v] == delta[s][a][v])

        elif clue['type'] == 'crime_different_from':
            # C_A != X_s,A
            s, a = clue['suspect'], clue['attribute']
            for v in self.domains[a]:
                model.Add(crime[a][v] + delta[s][a][v] <= 1)

        elif clue['type'] == 'indirect_positive':
            # ∃s: X_s,A1=v1 ∧ X_s,A2=v2
            a1, v1 = clue['attr1'], clue['val1']
            a2, v2 = clue['attr2'], clue['val2']

            # At least one suspect satisfies both
            exists_vars = []
            for s in self.suspects:
                both_true = model.NewBoolVar(f'both_{s}_{a1}_{v1}_{a2}_{v2}')
                model.AddMultiplicationEquality(
                    both_true,
                    [delta[s][a1][v1], delta[s][a2][v2]]
                )
                exists_vars.append(both_true)
            model.Add(sum(exists_vars) >= 1)

        elif clue['type'] == 'indirect_negative':
            # ∀s: X_s,A1=v1 ⇒ X_s,A2≠v2
            a1, v1 = clue['attr1'], clue['val1']
            a2, v2 = clue['attr2'], clue['val2']

            for s in self.suspects:
                # δ_s,A1,v1 <= 1 - δ_s,A2,v2
                model.Add(delta[s][a1][v1] + delta[s][a2][v2] <= 1)

    def is_true_murderer_feasible(self, clues):
        """Ensure we don't accidentally eliminate the true murderer"""
        return self._is_feasible_murderer(self.true_murderer, clues)
