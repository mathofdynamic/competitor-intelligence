# CI Package v1.1 contract

Package v1.1 is an additive minor evolution of `ci-package/v1`. It preserves the v1 Markdown file inventory, IDs, findings, source records and review boundary. Existing v1 packages remain accepted by the validator. New structured fields let importers build competitor pages and comparisons without parsing prose. The v1.1 JSON frontmatter schema is `schemas/ci-package-v1.1.json`; semantic checks live in `scripts/validate_package.py`.

## Inventory and common frontmatter

Use the same root files, dossiers, analyses, `sources/<source-id>.md` and `findings/<finding-id>.md` as v1, plus `analysis/CHANGELOG.md` only when a prior package is supplied. Every Markdown file starts with YAML frontmatter containing `schema_version: ci-package/v1.1`, `document_type`, `package_id`, `run_id` and timezone-qualified `generated_at`. All package documents use one schema version. Body text explains the structured fields but does not replace them.

The manifest still contains package/company/run IDs and names, timestamps, market scope, competitor/source/finding/direct counts, package status, generator and file count. `files` lists every canonical package document exactly once with relative path, document type and SHA-256. The safe builder only zips manifest-listed files and refuses unsafe paths, stale hashes and failed packages. `_work/`, caches, credentials, private captures and temporary files stay outside the package.

## Competitor directory and profile

`COMPETITORS.md.competitors[]` retains v1 identity/classification fields and adds:

- `brand_name`, `short_description` (factual synthesis, 1-3 sentences), `primary_categories`
- `dimension_coverage`, `coverage_metrics`, `research_gaps`
- optional `previous_competitor_id`/match metadata where used

Each competitor's `PROFILE.md` repeats normalized identity and classification, then includes nullable `business_model`, `primary_customer`, `primary_geography`, `sales_model`, `primary_offering`, `online_presence`, `physical_presence`, optional `logo_url`, `favicon_url`, `brand_initials`, geography observations, sales-channel entries and trust-signal entries. Use `profile_field_evidence` and evidence IDs for every populated factual field. Logo/favicon URLs are optional display metadata; never download or bundle arbitrary marketing imagery. Invalid logo URLs are warnings, not package failures. Initials require the documented deterministic derivation.

Do not infer physical or national presence from a domain or a single branch. `physical_presence` is `observed` or `unknown`; geography entries describe only what cited sources support.

## Dimension coverage and gaps

Every competitor has exactly one `dimension_coverage` map entry for each of the 12 standard dimensions: `identity`, `description`, `geography`, `offering`, `pricing`, `positioning`, `customer_experience`, `sales_channels`, `digital_presence`, `trust`, `promotions`, `physical_presence`.

Each entry contains:

```yaml
state: SUPPORTED # PARTIAL | SEARCHED_UNKNOWN | NOT_RESEARCHED | RESTRICTED
source_ids: []
finding_ids: []
query_ids: []
reason: null
```

`SUPPORTED`/`PARTIAL` require findings; `PARTIAL` states its limitation. `SEARCHED_UNKNOWN` requires targeted query IDs and a result note. `NOT_RESEARCHED` cannot include query/findings and needs a documented reason. A direct dossier with this state receives a warning so the gap remains visible. `RESTRICTED` cites a limiting source record and reason, and has no positive findings for that dimension. For direct competitors, every applicable core dimension is attempted or has a documented reason.

`research_gaps` repeats `SEARCHED_UNKNOWN`, `NOT_RESEARCHED` and `RESTRICTED` dimensions with state and note. A state is never converted into `false`, `0`, or a generic `unknown`.

`coverage_metrics` includes all five state counts, `coverage_percentage`, `research_attempt_percentage`, formula and limitations. Use equal weights only:

- coverage = (`SUPPORTED` + `PARTIAL`) / applicable dimensions * 100
- research attempted = (all states except `NOT_RESEARCHED`) / applicable dimensions * 100

For the standard dimensions the denominator is 12. State explicitly that these are evidence-coverage measures, not competitor quality or market completeness. `DISCOVERY.md.coverage.competitor_dimension_counts` aggregates each state for every standard dimension and uses the same formula note. Discovery query yield/saturation remains distinct from dossier coverage.

The focal company uses comparable fields and the same dimension names. User-provided facts retain provenance. When company identity/domain or a dimension is not researched, use explicit unknown/null data and a documented state/reason, not guessed matches.

## Structured comparable data

All machine-consumable values live in YAML frontmatter and reference atomic finding IDs:

- `OFFERINGS.md`: `product_categories` and `services` entries with controlled `key` and `finding_ids`. For eyewear, use the product/service vocabularies in `dimensions.md`. Unobserved taxonomy values are omitted, never false.
- `PRICING.md`: `price_observations` use either one numeric `amount` with `finding_id`, or an observed `amount_min`/`amount_max` pair with two atomic endpoint findings in `finding_ids`. Each record also contains `category`, `item_or_service`, original ISO currency, displayed `unit`, `price_type`, `promotion_state`, `observed_at` and `source_ids`. Source and finding currencies and units must match. Never silently convert currencies. For example, a price displayed in toman keeps the observed amount in toman, `currency: IRR` and `unit: toman`; it is not multiplied by ten. `price_summaries` group by category, currency and unit. For groups with at least two distinct observations, minimum is the lowest lower bound, maximum is the highest upper bound, median is the median of each item's midpoint, and count is the number of item/service observations. List every endpoint finding, formula and sampling limitation. These are observed samples, not market price estimates.
- `PRICING.md.promotions`: normalized promotion `type`, `state` (`current`, `historical`, `unknown`) and finding IDs. Dates and source context determine whether an offer is current.
- `POSITIONING.md.themes`: supported normalized theme keys and finding IDs; no subjective personality inference.
- `EXPERIENCE.md.capabilities`, `DIGITAL.md.capabilities`, `PROFILE.md.sales_channels_observed` and `PROFILE.md.trust_signals`: allowed normalized keys with finding IDs. Optional detailed terms use atomic findings for return days, warranty duration, delivery thresholds and similar values.
- Analysis `derived_metrics`: field, entity, value/unit, explicit formula, finding inputs and limitations. Breadth counts are descriptive. Relative price index and similarity require matched comparable evidence and a transparent formula. Never create an overall score, winner, market share or traffic estimate from site observations.
- Analysis `hypotheses`: evidence-backed opportunity/risk records with ID, type, title, summary, related competitor IDs, related finding IDs, evidence strength and limitations. They are hypotheses, not guaranteed recommendations. No hypothesis without linked findings.

Keep `OBSERVATION` separate from interpretation in finding bodies. Every finding is atomic, traceable and `needs_review`. Sources need public URLs, source type, publisher/title, collection/access metadata, content hash and bounded paraphrased evidence. Search snippets are discovery-only. All source/access policy rules from v1 remain in force.

## Change tracking

`RUN.md.previous_package_id` is null with no changelog. If supplied, validate the old package before comparison, preserve matched competitor IDs, and write `analysis/CHANGELOG.md`. `RUN.md.previous_competitor_matches` records old/current IDs, match basis and match strength. New discoveries have new IDs. A prior unknown becoming a supported observation is `newly_observed`, not proof of business change. Claims of pricing/policy/channel changes require comparable old and current findings; disappearance from the sample is not inactivity.

## Validation and packaging

Run fixture tests, `python scripts/validate_package.py <package-dir>`, then `python scripts/build_package.py <package-dir> --seal`, validate again, review warnings, and build with `python scripts/build_package.py <package-dir>`. A package with `FAIL` is never `import_ready`. Findings are never auto-approved. The manifest-only ZIP is portable and does not include work files or hidden captures.
