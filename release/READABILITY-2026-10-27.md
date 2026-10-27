# Documentation readability refresh — October 27, 2026

The owner requested a less dense, more readable public website, including clearer
CLI examples, formatting and images. This refresh updates the existing site and
repository; it does not create a new repository or change the default branch.

## Changes

- Rewrote all 14 content pages and the README around short explanations,
  reader-oriented headings, numbered tutorials and grouped reference material.
- Added a consistent reading layout, simpler navigation, quieter colors,
  readable line lengths, mobile contents menus, scrollable tables and clear
  next/previous links.
- Added copy buttons to multiline CLI/Python examples, with accessible status
  feedback. Commands wrap on small screens without changing copied text.
- Added three original explanatory SVGs and a saved-data accuracy overview,
  with a stacked version for phone screens. Existing detailed scientific plots
  remain available in expandable sections.
- Added a searchable, expandable parameter reference covering all 62 settings.
- Kept original studies, phase-specific counts, limitations, cost accounting,
  raw outcome downloads and source/checksum links available. Dollar displays
  retain two decimal places.

## Validation

- Strict MkDocs build passes.
- 15 focused interface, parameter-coverage and research-replay tests pass.
- All 947 generated internal links/assets/anchors were checked, including the
  hosted subpath used by the 404 page. No shell-example line exceeds 85 characters.
- Desktop layouts reviewed at 1280 px; every content page checked at 390 px
  with no page-level horizontal overflow or broken loaded images.
- Copy feedback, compact navigation, parameter search, anchored expansion and
  site-wide search verified through the browser. Numbered headings have explicit
  CSS-safe anchors; no new browser errors remained in the checked flows.
- Plotting script passes Ruff; browser script passes Node syntax checking.

Measured JSON, benchmark sources and package implementation are unchanged. No
paid model/image calls were made. The published v0.5.0rc2 tag and its candidate
artifacts are not replaced; this is a documentation update. The current static
export inventory and hashes are recorded in preview-site-manifest.json.
