#!/usr/bin/env python3
"""
Mystery Game - Main Entry Point
"""

from puzzle_generator import PuzzleGenerator
from cli_game import play_game
import time
from statistics import mean


def main():
    # Define suspects and domains for the mystery
    suspects = [
        'James Hartley',
        'Eleanor Blackwood',
        'Margaret Finch',
        'Marcus Webb',
    ]

    domains = {
        'weapon': [
            'Wrench',
            'Poison Vial',
            'Rope',
            'Bloody Handkerchief',
        ],
        'location': [
            'Master Bedroom',
            'Bathroom',
            'Study',
            'Kitchen',
        ],
        'motive': [
            'Inheritance',
            'Revenge',
            'Jealousy',
            'Blackmail',
        ],
        'time': [
            'Late Evening',
            'Midnight',
            '1:00 AM',
            '2:00 AM',
        ],
    }

    runs = 4
    print(f"Measuring puzzle generation time ({runs} runs)...\n")

    # Create generator once and measure generate() time multiple times
    generator = PuzzleGenerator(suspects, domains)
    times = []
    puzzle = None

    for i in range(runs):
        t0 = time.perf_counter()
        puzzle = generator.generate()
        t1 = time.perf_counter()
        elapsed = t1 - t0
        times.append(elapsed)
        print(f"Run {i+1}: {elapsed:.3f} s")

    avg = mean(times) if times else 0.0
    print(f"\nAverage generation time over {runs} runs: {avg:.3f} s\n")

    # Play the game using the last generated puzzle
    result = play_game(puzzle)
    print(f"Clue pool length: {result}")


if __name__ == "__main__":
    main()
