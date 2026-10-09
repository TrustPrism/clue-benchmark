# Source provenance

This is a standalone dataset-generator repository. Its sampling, clue predicates,
formatting and original integer solver descend from the TrustPrism clue generator.
`PROVENANCE.json` records that original source commit, working-tree changes and
imported byte hashes. Those hashes describe the import, not the current files.

The current implementation adds independently encoded corruption semantics,
sufficient-subset and coalition certification, deterministic presentation,
streamed dataset bundles and an explicitly authorized evaluation harness.
The original flat configuration and generate/validate/export interfaces remain
as a small compatibility layer. Retired study runners and original Unity/web
applications are not distributed with this package.

Ownership and redistribution permissions remain unresolved; see `LICENSING.md`.
