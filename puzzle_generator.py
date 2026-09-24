from world_sampler import WorldSampler
from clue_generator import ClueGenerator
from csp_solver import MysteryCSPSolver
from hardness_controller import HardnessController


class PuzzleGenerator:
    def __init__(self, suspects, domains):
        self.suspects = suspects
        self.domains = domains

    def generate(self, alpha=0.9, beta=0.9, max_clues=None):
        """
        Main generation pipeline
        Returns: Puzzle object with clues and hidden solution
        """
        # 1. Sample world
        sampler = WorldSampler(self.domains)
        world, murderer = sampler.sample_world(self.suspects)

        # 2. Build clue pool
        clue_gen = ClueGenerator(world, murderer, self.domains)
        clue_pool_len = clue_gen.build_clue_pool()

        # 3. Create solver
        solver = MysteryCSPSolver(self.suspects, self.domains, world, murderer)

        # 4. Select clues with hardness control
        hardness = HardnessController(alpha, beta)
        selected_clues = hardness.select_clues(
            clue_gen.clue_pool,
            max_clues,
            solver
        )

        # 5. Validate uniqueness
        if not solver.is_unique(selected_clues):
            # Retry or add more clues
            next_max_clues = (
                None if max_clues is None else max_clues + 5
            )
            return self.generate(alpha, beta, next_max_clues)

        # 6. Package puzzle
        puzzle = {
            'suspects': self.suspects,
            'domains': self.domains,
            'clues': selected_clues,
            'solution': {
                'murderer': murderer,
                'world': world
            },
            'metadata': {
                'alpha': alpha,
                'beta': beta,
                'num_clues': len(selected_clues),
                'clue_pool_len': clue_pool_len
            }
        }

        return puzzle
