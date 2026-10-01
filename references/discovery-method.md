# Discovery and coverage

Direct competition requires meaningful overlap in customer, problem, offering and geography/channel. Indirect firms partially overlap; substitutes solve the problem differently; aspirational/reference firms inform comparison outside current competition. Exclusions retain reasons. Verification (`confirmed`, `candidate`) is separate from classification. Search snippets cannot confirm overlap.

Use at least three independent relevant families, including category, local-language and geography/channel where applicable. Add English/alternate product terms, similar-to/comparison, price tiers, retailers/marketplaces, directories and reference links when useful. Explain skipped families. Translation variants alone are not independent coverage.

Each query records `query_id`, `family`, `query`, `language`, `geography`, `searched_at`, `sources_searched`, `result_urls`, `new_competitor_ids`, `duplicate_ids`, `excluded_ids`, `limitations`. Verify landing pages before accepting identities. Record tool result limits and blocked languages/sources.

Normalize domains to lowercase IDNA hosts; retain aliases/redirects. Resolve localized domains and parent/sub-brand relations using identity evidence, not name similarity. `identity_groups` record canonical_id, aliases, domains, relationship, source_ids and decision. Stable IDs survive renames. Preserve uncertain relationships.

Saturation: after broad initial coverage, require three consecutive independent relevant query families adding zero credible new identities. Reset the streak after a new credible identity; credible pending candidates count. This heuristic does not establish statistical recall. Budget/access stops set `saturation_reached: false`.

DISCOVERY frontmatter: queries, identity_groups, exclusions, coverage, saturation. Coverage records covered/uncovered scope slices, confirmed/candidate/excluded counts, deferred subjects and uncertainty. Saturation records rule, zero_new_family_streak, saturation_reached, stop_reason. Describe comprehensive scoped coverage within these limits, never all competitors globally.
