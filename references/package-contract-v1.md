# CI Package v1 contract

V1 remains supported for existing packages and legacy import compatibility. For new depth-oriented dossiers use the additive minor extension `ci-package/v1.1` documented in [package-contract-v1.1.md](package-contract-v1.1.md). It preserves the v1 inventory and atomic evidence model while adding explicit per-dimension states and comparable structured fields. Do not silently label a v1.1 package as v1.

Canonical records are UTF-8 Markdown with YAML frontmatter beginning at the first line. Full YAML mappings/lists are supported through PyYAML safe loading; duplicate keys, aliases, anchors and explicit tags are rejected. Quote timezone-qualified ISO timestamps. IDs are lowercase letters/digits/underscore/hyphen, 1–120 characters. Paths use portable ASCII names, forward slashes, no traversal, case collisions, reserved Windows names or symlinks. Python 3.10+; install `scripts/requirements.txt`.

## Inventory

```text
competitor-intelligence-package/
  MANIFEST.md
  COMPANY.md
  RUN.md
  RESEARCH-PLAN.md
  DISCOVERY.md
  COMPETITORS.md
  VALIDATION.md
  competitors/<competitor-id>/
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
    CHANGELOG.md                   # only with a previous package
  sources/<source-id>.md
  findings/<finding-id>.md
```

RESEARCH-PLAN is an additional required root document. Excluded candidates live in `COMPETITORS.md.excluded_candidates`; included candidates can have dossiers with explicit unknowns. A directory slug equals competitor ID. No _work, cache, binary captures, credentials, screenshots or unlisted files may appear, even if harmless. Work lives in a sibling directory.

## Frontmatter

Every file: schema_version (`ci-package/v1`), document_type, package_id, run_id, generated_at. Common structured definitions are in `schemas/ci-package-v1.json`; semantic/reference/hash validation is implemented in validate_package.py. Body is a nonempty human explanation, never required for chart extraction.

| Path | document_type | Additional structured fields |
| --- | --- | --- |
| MANIFEST | manifest | company_id, company_name, created_at, research_started_at, research_finished_at, market_scope, competitor_count, source_count, finding_count, direct_competitor_count, package_status, generator, file_count, files |
| COMPANY | company | company_id, company_name, canonical_domain, description, industry, sub_industries, products_services, target_segments, geographies, languages, sales_channels, known_price_position, known_competitors, research_goals, inclusions, exclusions, unknowns, evidence_coverage, profile_provenance, finding_ids |
| RUN | run | research_mode, concurrency, budgets, extension_dimensions, conflict_groups, previous_package_id (null absent), limitations |
| RESEARCH-PLAN | research_plan | market_scope, criteria, discovery_strategy, search_vocabulary, dimensions, limitations |
| DISCOVERY | discovery | queries, identity_groups, exclusions, coverage, saturation |
| COMPETITORS | competitor_directory | competitors, excluded_candidates |
| VALIDATION | validation | result (PASS/WARNING/FAIL), checks, validator, hash_check |
| PROFILE | competitor_profile | competitor_id, name, domain, classification, verification_status, geographies, primary_categories, reason_for_inclusion, dimensions, finding_ids, limitations |
| Other dossiers | competitor_offerings/pricing/positioning/experience/digital/evidence | competitor_id, dimensions, finding_ids, source_ids, rows, limitations |
| Analyses | analysis | dimensions, finding_ids, rows, derived_metrics, hypotheses, limitations |
| CHANGELOG | changelog | previous_package_id, changes, limitations |
| Source | source | source_id, competitor_id, url, canonical_url, source_type, publisher, title, accessed_at, collection_method, access_class, access_reason, restriction_scope, reuse_mode, robots_status, terms_status, content_sha256, evidence_text, status; optional policy_url |
| Finding | finding | finding_id, competitor_id, dimension, field_key, observed_value, value_type, observed_at, source_ids, evidence_strength, review_status, notes; conditional normalized_value, currency, unit |

Competitor entries contain id, name, domain, classification, verification_status, geographies, primary_categories, reason_for_inclusion, identity_source_ids, relevance_source_ids, evidence_coverage, last_observed_at. Included records require traceable identity and relevance sources. A confirmed competitor requires at least one direct-allowed relevance finding; discovery-only support can establish identity/candidate status but not detailed facts. Classifications: direct, indirect, substitute, aspirational/reference, excluded. Verification: confirmed/candidate. Excluded records have id/name/domain/reason and discovery references; they get no dossiers. Counts exclude excluded records; direct count is classification count, not confirmed-only. Coverage reports verified counts separately.

Sources may belong to the focal company using competitor_id = company_id. Source types: official_product, official_pricing, official_docs, official_company, official_press, public_social, retailer, marketplace, directory, third_party, search_snippet. Methods: browser_public, http_public, manual_review, public_search. `access_class`: DIRECT_ALLOWED, DISCOVERY_ONLY, DIRECT_PROHIBITED, UNKNOWN. `restriction_scope`: direct_access, content_reuse, commercial_reuse, other, unknown. `reuse_mode`: paraphrase_only, short_quote, metadata_only, none. `access_reason` explains the classification; `policy_url` is optional. Status: collected, blocked, unverified, stale. Robots: allowed/disallowed/unknown. Terms: reviewed_allowed/reviewed_restricted/unknown. A copying/commercial-reuse restriction alone does not prohibit factual observation. `DIRECT_ALLOWED` requires a reachable public path, robots to allow it, and no explicit prohibition on the intended observation. Terms may be unknown; this does not grant content-reuse rights. Findings require `reuse_mode: paraphrase_only` and bounded original paraphrase/normalized evidence; no copied source wording is retained. `DISCOVERY_ONLY` records are metadata-only with empty evidence and cannot support detailed findings. `DIRECT_PROHIBITED` records are not fetched for the run and have no content. `UNKNOWN` records are not deep-collected. Search snippets never support findings. All empty evidence hashes equal SHA-256 of the empty UTF-8 string.

Every included competitor carries a dimension map `evidence_coverage`, keyed by each declared dimension with one of: complete, good, partial, limited, unknown, not_researched. Coverage describes research depth, not company quality. Analysis cells separately use observed, user_provided, unknown, not_researched, or conflict; observed absence is represented only by an explicit boolean false finding. Missing evidence never means unavailable.

Profile provenance, analysis rows, metric and hypothesis shapes are specified in research-method.md and report-format.md. Observation bodies separate Observed/Interpretation/Limitations. None of the generated findings may be approved.

## Checksums and sealing

`files` is a list of mappings with path, document_type, sha256. Every canonical file, including MANIFEST and VALIDATION, is listed exactly once. Ordinary files use SHA-256 of exact bytes. MANIFEST uses `manifest-self-blank-v1`: parse its frontmatter, blank only files[path=MANIFEST.md].sha256, then hash UTF-8 compact sorted-key JSON of `{frontmatter: ..., body: ...}` with ensure_ascii=false and separators comma/colon. Body is the exact text after the closing delimiter. Date strings remain strings. See package_io.digest for normative implementation. This avoids an impossible self-referential byte hash; it is an integrity check, not a signature.

After authoring, `build_package.py <dir> --seal` refreshes counts and validation report, sets import_ready only without FAIL, and computes hashes. It deliberately rehashes edited files; use only as an authoring step, never to conceal an unexplained hash mismatch. Ordinary validation/build never repairs hashes. Re-run validation after sealing. A WARNING package can be imported for review with visible limitations. FAIL is never import-ready; structural readiness does not approve evidence.

The seal command generates VALIDATION.md, including on first authoring; do not invent a PASS report manually. Other required records must already exist. The main agent reviews the actual checks after sealing.

Only validated manifest entries enter `<company-id>-competitor-intelligence-<run-date>.zip`, under the single `competitor-intelligence-package/` root. Build output must be outside the package; existing ZIPs are not overwritten. No external fetches or application writes occur.

## Previous-run comparison

Validate the supplied previous package first. Preserve its package ID and map stable identities/fields/context. `changes` contains change_id, entity_id, dimension, field_key, change_type, previous_value, current_value, previous_finding_ids, current_finding_ids, interpretation, limitations. Previous finding IDs refer to the supplied previous package, not the current finding directory. Types: new_competitor, removed_or_inactive, not_observed, pricing, offering, positioning, service_policy, channel_feature. Removal/inactivity needs positive evidence; disappearance from sampling is not_observed. No prior package means previous_package_id null and no CHANGELOG. Findings remain snapshots; do not fabricate changes.

Optional deterministic helper: `python scripts/compare_packages.py <previous-dir> <current-dir>` after independently sealing/validating both snapshots. It writes CHANGELOG and updates RUN.previous_package_id. Review the draft differences, then seal/validate the current package again. It never infers inactivity; the main agent must reconcile scope, identities and conflicts. Current-package validation checks current references; the main agent verifies previous references against the retained prior package.
