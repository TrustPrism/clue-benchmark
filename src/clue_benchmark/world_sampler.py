import random


class WorldSampler:
    def __init__(self, domains):
        """
        domains = {
            'weapon': ['Wrench', 'Poison Vial', 'Rope', 'Bloody Handkerchief'],
            'location': ['Master Bedroom', 'Bathroom', 'Study', 'Kitchen'],
            'motive': ['Inheritance', 'Revenge', 'Jealousy', 'Blackmail'],
            'time': ['Late Evening', 'Midnight', '1:00 AM', '2:00 AM'],
        }
        """
        self.domains = domains
        self.attributes = list(domains.keys())

    def sample_world(
        self,
        suspects,
        require_unique_murderer_profile=False,
        max_attempts=1000,
        rng=None,
    ):
        """
        Returns: (world_state, murderer)
        world_state: Dict[suspect][attribute] = value
        murderer: selected suspect
        """
        rng = rng or random
        for _ in range(max_attempts):
            world = {}
            for suspect in suspects:
                world[suspect] = {}
                for attr in self.attributes:
                    # Uniform random choice (values CAN repeat)
                    world[suspect][attr] = rng.choice(self.domains[attr])

            murderer = rng.choice(suspects)
            if not require_unique_murderer_profile or self._has_unique_profile(
                world, murderer
            ):
                return world, murderer

        raise RuntimeError("Could not sample a world with a unique murderer profile.")

    def _has_unique_profile(self, world, murderer):
        murderer_profile = world[murderer]
        for suspect, attrs in world.items():
            if suspect != murderer and attrs == murderer_profile:
                return False
        return True
