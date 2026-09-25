from clue_formatter import ClueFormatter


def play_game(puzzle):
    print("Mystery Game\n")
    print(f"Suspects: {', '.join(puzzle['suspects'])}\n")

    for i, clue in enumerate(puzzle['clues'], 1):
        print(f"{i}. {ClueFormatter.format(clue)}")

    print("\nWho is the murderer?")
    print("# Clues")
    guess = input("> ")

    if guess == puzzle['solution']['murderer']:
        print("Correct! You solved it!")
    else:
        print(f"Wrong. It was {puzzle['solution']['murderer']}")
    
    return puzzle['metadata'].get('clue_pool_len', 0)
 