# Competitor Intelligence

An evidence-first local agent skill for competitor discovery, public-source research, and portable competitive analysis.

Give your coding agent a company brief. The skill orchestrates scoped discovery, bounded competitor research, evidence reconciliation, dimensional comparison, and a validated Markdown package. Findings remain pending human review.

## What it produces

- A normalized company profile with user-provided, observed, inferred, and unknown information distinguished.
- A discovery log with query families, identity deduplication, exclusions, coverage, and saturation assessment.
- Twelve-dimension competitor dossiers covering identity, description, geography, offerings, prices, positioning, customer experience, sales and digital channels, trust, promotions, and physical presence.
- Explicit per-dimension states: `SUPPORTED`, `PARTIAL`, `SEARCHED_UNKNOWN`, `NOT_RESEARCHED`, or `RESTRICTED`.
- Structured price observations, normalized eyewear categories and capabilities, coverage metrics, and evidence-backed opportunity/risk hypotheses.
- Atomic findings linked to dated, bounded source evidence.
- Cross-competitor matrices, market analysis, opportunity hypotheses, and visible conflicts and unknowns.
- An optional manifest-validated ZIP suitable for downstream review ingestion.

This is a portable research workflow. It does not require an application database or a particular research API. It does not claim to discover every competitor globally, approve findings, rank companies with opaque scores, or infer market share from websites.

## Install locally

Requirements: Python 3.10+, PyYAML, and an agent with public search or browser access for actual research. Package validation and ZIP tooling run offline.

Clone the repository into your agent's local skill directory:

```sh
git clone https://github.com/mathofdynamic/competitor-intelligence.git ~/.codex/skills/competitor-intelligence
cd ~/.codex/skills/competitor-intelligence
python -m pip install -r scripts/requirements.txt
```

On Windows PowerShell:

```powershell
git clone https://github.com/mathofdynamic/competitor-intelligence.git "$env:USERPROFILE\.codex\skills\competitor-intelligence"
Set-Location "$env:USERPROFILE\.codex\skills\competitor-intelligence"
python -m pip install -r scripts/requirements.txt
```

For another agent, copy the entire folder into its supported skill directory. Preserve `SKILL.md`, references, schemas, and scripts. Multi-agent tools are optional: research falls back to sequential assignments with the same output contract.

## Invoke

```text
Use $competitor-intelligence.

Company: Example Optics
Website: https://example.com
Description: prescription frames and sunglasses sold online
Customers: adults buying eyewear online
Market: Iran; Persian-language research, English where useful
Goals: compare offerings, visible prices, returns and purchase mechanisms
Known competitors: none supplied
Exclude: wholesale-only suppliers
Budget: 20 credible subjects, 12 pages per subject, 90 minutes total
Output: ./research/example-optics/
Previous package: none
Create a ZIP.
```

This brief is illustrative; it asserts no real competitor facts. See [the complete input example](examples/company-brief.md). You do not need to prompt separately for discovery, research, reports, or packaging.

## Research workflow

1. Normalize company understanding, market scope, and unknowns; write the research plan.
2. When a prior package exists, validate it, keep stable IDs, and identify stale or shallow dimensions.
3. Deepen existing direct competitors before expanding discovery on recovery runs; otherwise discover broadly through independent query families.
4. Deliberately attempt all 12 standard dimensions for every direct competitor, using multiple relevant source types and alternative permitted sources where needed.
5. Delegate one competitor per researcher, up to four concurrent workers within available capacity; batch large sets or fall back to sequential research.
6. Have the main agent verify identities, source links, claims, currencies, and terminology; reconcile contradictions and synthesize comparable analysis.
7. Seal, validate, review warnings, and optionally ZIP the package.

Discovery saturation requires three consecutive independent relevant query families producing no credible new identities after initial broad coverage. Budget or access stops are reported separately. Saturation is a practical coverage heuristic, not proof of global completeness.

## CI Package v1.1

New packages use the backward-compatible additive minor contract `ci-package/v1.1`. Existing v1 packages remain supported. Canonical records are Markdown with machine-readable YAML frontmatter; structured chart values belong in frontmatter, and prose supplies explanations.

```text
competitor-intelligence-package/
  MANIFEST.md
  COMPANY.md
  RUN.md
  RESEARCH-PLAN.md
  DISCOVERY.md
  COMPETITORS.md
  VALIDATION.md
  competitors/<id>/
    PROFILE.md
    OFFERINGS.md
    PRICING.md
    POSITIONING.md
    EXPERIENCE.md
    DIGITAL.md
    EVIDENCE.md
  analysis/
    EXECUTIVE-SUMMARY.md
    MARKET-MAP.md
    COMPARISON.md
    OFFERING-MATRIX.md
    PRICING-ANALYSIS.md
    POSITIONING.md
    CUSTOMER-EXPERIENCE.md
    DIGITAL-PRESENCE.md
    OPPORTUNITIES.md
    RISKS-AND-UNKNOWNS.md
    CHANGELOG.md                 # only with a previous package
  sources/<source-id>.md
  findings/<finding-id>.md
```

Every finding is atomic, dated, linked to sources, and marked `needs_review`. Evidence strength describes support quality, not company quality. Unknowns remain unknown; contradictions remain visible. The focal company uses the same comparable dimensions.

Each competitor dimension has a coverage state and source/query/finding references. `SEARCHED_UNKNOWN` means targeted searches found no reliable claim; `NOT_RESEARCHED` means no meaningful attempt; `RESTRICTED` records the access barrier. The validator checks direct-dossier gaps, structured prices, controlled capability values, source diversity, evidence references, previous-run mappings and manifest hashes. Coverage percentage measures evidence coverage, never competitor quality.

See the [v1.1 package contract](references/package-contract-v1.1.md), [v1 compatibility contract](references/package-contract-v1.md), [evidence model](references/evidence-schema.md), and [research dimensions](references/dimensions.md). Existing JSON schemas are retained legacy adapter contracts.

## Validate and package

Run these commands from the installed skill directory, using your authored package path:

```sh
python scripts/build_package.py <package-dir> --seal
python scripts/validate_package.py <package-dir>
python scripts/build_package.py <package-dir>
```

`--seal` is an explicit authoring operation: it creates the validation report, refreshes counts and hashes, and marks structural import readiness only when no FAIL remains. Normal validation and ZIP building never repair hashes.

The validator checks required files, YAML/frontmatter, supported versions and values, identities, evidence references, dates, currency, public URL syntax, chart consistency, counts, and hashes. FAIL exits nonzero and blocks ZIP creation. WARNING preserves reviewable limitations.

The ZIP builder includes only validated manifest entries, rejects unsafe paths and linked files, refuses overwrite, and prints the final ZIP SHA-256. Output is `<company-id>-competitor-intelligence-<run-date>.zip` with one `competitor-intelligence-package/` root. The manifest has a documented self-blank hashing rule to avoid a circular checksum.

For previous-run comparison:

```sh
python scripts/compare_packages.py <previous-dir> <current-dir>
```

Both snapshots must validate first. Review the generated differences, then seal and validate the current package again. Missing observations are not proof of inactivity.

## Safety and review

Research uses public sources only, official pages first. No credentials, private APIs, login/paywall/CAPTCHA bypass, account creation, competitor contact, form submissions, purchases, posting, support interactions, or private customer data.

Respect robots guidance, source terms, aggregate request rates, and copyright. Evidence is bounded; full copyrighted pages, browser profiles, cache, credentials, and temporary captures never enter the package. `_work/` is a sibling working directory, not package content.

Human or application review decides approval later. `import_ready` means structurally valid for review ingestion, not approved evidence or verified compatibility with a particular importer. Offline URL checks do not prove DNS ownership, safe redirects, or factual truth.

## Tests

```sh
python tests/validate_fixtures.py
python -m unittest discover -s tests -p "test_*.py"
```

The suite contains offline v1 and v1.1 package tests, including coverage states, multi-source attempts, price normalization/summaries, capability taxonomies, optional branding, opportunity/risk evidence, previous-run identity matching, conflicts, malicious paths, copied-skill execution, and ZIP round trips. Fixtures are synthetic. Tests do not establish live research quality or application integration.

## Repository layout

| Path | Purpose |
| --- | --- |
| `SKILL.md` | Agent entrypoint and complete orchestration |
| `references/` | Discovery, evidence, safety, research and output contracts |
| `schemas/` | Frontmatter contract, supported currencies, legacy JSON contracts |
| `scripts/` | Offline validation, sealing, ZIP and comparison tooling |
| `examples/` | Illustrative input and finding records |
| `tests/` | Synthetic fixtures and regression tests |
| `PUBLICATION_MANIFEST.md` | Distribution scope and excluded private artifacts |

## License

No open-source license has been selected. Public visibility does not grant an additional reuse or redistribution license. The owner may add one separately.
