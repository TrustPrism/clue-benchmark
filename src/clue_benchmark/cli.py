"""Dataset CLI with a small compatibility surface for flat puzzle configs."""

import sys

from .community_cli import main as dataset_main


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in {"generate", "validate", "export"}:
        from .legacy_cli import main as compatibility_main

        return compatibility_main(argv)
    return dataset_main(argv)
