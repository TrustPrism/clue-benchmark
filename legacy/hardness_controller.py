import random


class HardnessController:
    MAX_GREEDY_CANDIDATES = 24

    def __init__(self, alpha, beta):
        """
        alpha: P(direct clue) ∈ [0,1]
        beta: P(indirect_positive | complex) ∈ [0,1]
        """
        self.alpha = alpha
        self.beta = beta

    def select_clues(self, clue_pool, max_clues=None, solver=None):
        """
        Greedy selection using hardness probabilities
        Returns: list of selected clues
        """
        if solver is None:
            raise ValueError("solver is required")

        selected = []
        remaining_pool = clue_pool.copy()
        effective_max_clues = max_clues if max_clues is not None else len(remaining_pool)
        all_attributes = set()
        for clue in clue_pool:
            all_attributes.update(self._clue_attributes(clue))
        covered_attributes = set()

        while len(selected) < effective_max_clues and remaining_pool:
            # Determine clue type based on hardness
            is_direct = random.random() < self.alpha

            if is_direct:
                candidates = [c for c in remaining_pool
                             if c['difficulty'] in ['easy', 'medium']]
            else:
                # Complex mode
                is_positive = random.random() < self.beta
                if is_positive:
                    candidates = [c for c in remaining_pool
                                 if c['type'] == 'indirect_positive']
                else:
                    candidates = [c for c in remaining_pool
                                 if c['type'] == 'indirect_negative']

            if not candidates:
                break

            # Prefer candidates that expand attribute coverage when possible.
            uncovered_attributes = all_attributes - covered_attributes
            if uncovered_attributes:
                diverse_candidates = [
                    c for c in candidates
                    if self._clue_attributes(c) & uncovered_attributes
                ]
                if diverse_candidates:
                    candidates = diverse_candidates

            # Bound candidate evaluation cost for large pools.
            if len(candidates) > self.MAX_GREEDY_CANDIDATES:
                candidates = random.sample(candidates, self.MAX_GREEDY_CANDIDATES)

            # Choose candidate that maximally reduces feasible murderers
            best_clue = self._greedy_select(candidates, selected, solver)
            selected.append(best_clue)
            remaining_pool.remove(best_clue)
            covered_attributes.update(self._clue_attributes(best_clue))

            # Early termination if uniqueness achieved
            if solver.is_unique(selected):
                break

        return selected

    def _greedy_select(self, candidates, current_clues, solver):
        """Select clue that minimizes # feasible murderers"""
        best_clue = None
        min_feasible = float('inf')
        best_new_attr_coverage = -1
        covered_attributes = set()
        for clue in current_clues:
            covered_attributes.update(self._clue_attributes(clue))

        for clue in candidates:
            test_set = current_clues + [clue]
            num_feasible = solver.count_feasible_murderers(test_set)
            new_attr_coverage = len(
                self._clue_attributes(clue) - covered_attributes
            )

            # Keep true murderer feasible (critical!)
            if not solver.is_true_murderer_feasible(test_set):
                continue

            if num_feasible < min_feasible:
                min_feasible = num_feasible
                best_clue = clue
                best_new_attr_coverage = new_attr_coverage
            elif (
                num_feasible == min_feasible
                and new_attr_coverage > best_new_attr_coverage
            ):
                best_clue = clue
                best_new_attr_coverage = new_attr_coverage

        return best_clue if best_clue else candidates[0]

    def _clue_attributes(self, clue):
        """Return the set of attributes referenced by a clue."""
        clue_type = clue.get('type')

        if clue_type in ['unary_positive', 'unary_negative', 'crime_positive']:
            return {clue['attribute']}

        if clue_type in ['indirect_positive', 'indirect_negative']:
            return {clue['attr1'], clue['attr2']}

        return set()
