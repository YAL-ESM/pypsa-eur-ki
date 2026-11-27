---
name: nda
description: Non-disclosure rules for this repo - no confidential site information (exact coordinates, BRL offers per site, addresses or contact details of landowners) may reach git, GitHub or any outside service. Load it before every git add, commit, push or pull request, and whenever you work with the Brazil site shortlist or with anything derived from it.
---

<!--
SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>

SPDX-License-Identifier: CC-BY-4.0
-->

# NDA

Some Brazil site information is under NDA. It stays in this workspace. Nothing below goes into a commit,
a branch or commit name, a pull request, an issue, a pushed file or any outside service.

## Never push

1. **Exact coordinates** of a site (lat/lon, also rounded to a few decimals, or a marker for a single site on a map).
2. **BRL offers per site**: CAPEX, OPEX and lease offers, also converted to EUR, another year or an annuity.
3. **Addresses and contact details**: landowner names, e-mail addresses, phone numbers, postal addresses, also in part.

Anything from which these can be recovered counts as the value itself.

## Allowed

- Site id, state, municipality, technology, area, buildable MW, measured capacity factor, distance to grid
  and coast, nearest port.
- Coordinates and potentials that come from public data (ERA5 cells, land cover, WDPA), as long as they are not
  the NDA site positions.
- Aggregates over offers only after asking the user: with few sites per technology they reveal single offers.

## How

- The source is `workshop/inputs/site_shortlist.csv`. It is untracked and listed in `.git/info/exclude`. Never
  `git add` it, never with `-f`, never copy it or a subset of its columns to a tracked path.
- Read it at run time by path. Never paste values into scripts, configs, cost files, tests or notebooks.
- Write derived files that carry these values only to ignored paths (`results/`, `resources/`). Check with
  `git check-ignore -v <path>`. Note that `git add -f` overrides the ignore.
- For slides or GitHub show sites by state or municipality.
- Check the staged changes before every commit and push with the leak check in the skill
  `confidential-site-data` ("Before every commit or push"). It also covers the details of the rules above.
- If something confidential is in a commit that is not pushed yet, rewrite that commit. If it was already
  pushed, stop and tell the user: a new commit does not remove it from the history.
- If unsure whether something is covered, do not push it and ask.
