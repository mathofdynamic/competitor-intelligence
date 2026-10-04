# Package v1 atomic evidence

Package v1 uses snake_case YAML frontmatter; see package-contract-v1.md and schemas/ci-package-v1.json. One finding asserts one entity/dimension/field/context observation. Required: finding_id, competitor_id, dimension, field_key, observed_value, value_type, observed_at, source_ids, evidence_strength, review_status (`needs_review`), notes. Conditional: normalized_value, unit, currency, normalization_rule, context, conflict_group_id. Scalar values only; categories/capabilities become separate findings. Changed observations get new IDs with supersedes_finding_id where appropriate.

For new deep dossiers use the additive v1.1 minor contract in `package-contract-v1.1.md` and `schemas/ci-package-v1.1.json`. Keep a finding atomic and keep its normalized value separate from interpretation. The 12 v1.1 dimensions are identity, description, geography, offering, pricing, positioning, customer_experience, sales_channels, digital_presence, trust, promotions and physical_presence. Typed profile/taxonomy/price observations must reference the finding IDs that support them. Capability entries are positive observations only; absence is never inferred from an omitted key. A displayed price range uses separate scalar money findings for its minimum and maximum; preserve displayed denominations such as toman as the unit and never silently convert.

Observed value contains no analysis. Body separates Observed, Interpretation, Limitations. Types: text, number, integer, boolean, money. Money requires numeric value, ISO-4217 currency and unit. schemas/currencies.txt is the supported version snapshot; newly issued codes need a documented contract update. IRT is unsupported; explicit toman uses observed text plus IRR normalization. Unknown creates no finding.

Strength describes support: strong = direct official product/pricing; medium = official secondary support; weak = credible third-party or ambiguous observation. Ownership alone does not prove strength. Retain third-party attribution and ambiguity.

Only a `DIRECT_ALLOWED` source with bounded nonempty evidence can support a factual finding. `DISCOVERY_ONLY`, `DIRECT_PROHIBITED`, and `UNKNOWN` sources never support findings. Search snippets are discovery-only. Discovery-only/blocked/unverified sources preserve identity, access, and coverage gaps without copying content. Source `content_sha256` hashes exact bounded `evidence_text` UTF-8 bytes; metadata-only sources hash the empty string.

Dimension coverage is not a finding. Every v1.1 competitor dimension uses exactly one state: `SUPPORTED`, `PARTIAL`, `SEARCHED_UNKNOWN`, `NOT_RESEARCHED` or `RESTRICTED`. Search attempts and access restrictions remain explicit even when they produce no finding. Do not create a synthetic zero, negative capability, or factual claim to fill a dashboard cell. A current discovery can supplement an old snapshot; it cannot silently rewrite the date or provenance of that snapshot.

`access_class` describes permission to observe directly; `reuse_mode` describes what expression may be retained. Do not equate a restriction on commercial reuse with a ban on factual observation. When observation is permitted but content reuse is restricted, store normalized values and original paraphrases only. Include `access_reason`, `restriction_scope`, and any known policy URL. Never use long quotations or copy page prose.

Contradictions are separate findings sharing conflict_group_id. RUN.conflict_groups records conflict_group_id, finding_ids, interpretation, optional preferred_finding_id and justification. Referenced findings supply values, dates and sources. Preference requires matched scope and a reason; preserve both. Comparison cells mark conflict and null value rather than silently selecting one.

The following historical model applies only to legacy JSON adapters, not generated Package v1 records.

# Legacy evidence and finding model

Use the JSON schemas as the machine-readable contract.

Every source has an immutable `id`, canonical URL, source type, ownership context, observation time, collection conditions and evidence manifest. Every finding has an immutable `id`, `version`, `sourceId`, observed text, optional normalized value, interpretation, confidence, limitations, conflict group and review state.

The following distinctions are mandatory:

- `observedText`: what the public source visibly states or exposes.
- `normalizedValue`: a typed value with currency or unit and the conversion rule, if any.
- `interpretation`: an analyst statement that must not be presented as source text.
- `limitations`: missing context, localization, date uncertainty or sampling limits.
- `status`: candidate, needs review, approved, rejected, stale or conflict.
- `evidence.sha256`: checksum of a bounded private capture or normalized excerpt manifest, never a claim that the source is still unchanged.

An approved finding must retain its source URL, observation time and reviewer decision. A report must omit rejected, stale and unresolved-conflict findings.
