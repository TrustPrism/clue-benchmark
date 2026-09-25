# Private preview release status

The implementation, dataset, baseline experiments, and report are prepared in this private repository. Public release is intentionally deferred by the project owner.

Before public publication:

1. Resolve source-code ownership and select code/data licenses. Update licensing, package metadata, and Croissant metadata together.
2. Review generated cases, sampling-bias diagnostics, and the paper's bounded claims. Run a separately budgeted model study before drawing conclusions about LLM capabilities.
3. Freeze a new immutable version when generator semantics, prompts, scoring, or sampling change. Regenerate the dataset if generation changes; rerun results if the agent protocol changes. Preserve unchanged dataset hashes and never overwrite a published version silently.
4. Choose and verify a future publication venue's current requirements. Provide accessible code and dataset hosting, reproducible commands, citation metadata, and core/responsible-use dataset metadata.
5. Only then change visibility or publish to a package registry/data host. No automation in this repository performs those actions.

For this private preview, run `python scripts/check_release.py`, package build, unit/integration tests, and the source-isolation check before sharing the review branch. The initial baseline commit remains available on main and in Git history.
