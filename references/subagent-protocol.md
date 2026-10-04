# Bounded competitor researcher

After discovery and identity deduplication, assign one competitor per researcher. Default maximum is four concurrent researchers, reduced to available slots. Batch large sets and obey aggregate per-host request limits. RUN records subagent or sequential mode, planned/actual concurrency, budgets and outcomes. Sequential fallback preserves the same checklist and output fields.

Each assignment supplies:

- assignment ID and one competitor ID, name, domain, aliases and parent/sub-brand notes
- concise focal-company summary with provenance, market definition and inclusion scope
- classification criteria and why this candidate is relevant
- the 12 standard dimensions and industry-specific extensions
- previous-package facts, stable identity mapping, weak/old dimensions and observation dates, if supplied
- source-policy classes, alternatives for restricted official sources, bounded evidence limits and rate limits
- page/time budgets, query log expectations and an isolated `_work/<assignment-id>/` destination
- output schema: findings, sources, source attempts, query attempts, dimension coverage, gaps, conflicts and identity concerns

For each direct competitor, attempt identity, description, geography, offering, pricing, positioning, customer experience, sales channels, digital presence, trust, promotions and physical presence. Research multiple appropriate source types. A page quota is not a substitute for dimension coverage. If a dimension cannot be attempted, return `NOT_RESEARCHED` with a concrete reason. If targeted searches fail to establish a fact, return `SEARCHED_UNKNOWN` with query IDs. Use `RESTRICTED` only when source/access conditions prevented meaningful work, with the source record and reason. Do not mark items absent just because a worker did not find them.

Return structured atomic findings with source IDs and observation timestamps, plus normalized profile/taxonomy entries that reference those findings. Do not put interpretations in `observed_value`; distinguish observation, interpretation and limitations. Price records preserve exact currency and link to one finding. Use only public sources. Never create a finding from a search snippet, use credentials, bypass a restriction, contact a competitor or interact with customer-facing controls. Every finding is `needs_review`.

The main agent owns canonical IDs and files. It opens the linked public source when possible, checks access class, source/finding identity, claim-to-evidence match, dates, currency, taxonomy, aliases, duplicates and conflicts; recalculates derived values; and removes unsupported assertions. It reconciles terms across competitors, reviews all dimension-state maps and discovery logs, and owns all cross-market conclusions. A worker's declaration that work is complete is not a completion check.

If a worker times out, salvage only supported records, retain all attempted query/source results, mark unfinished dimensions with explicit states and reasons, and continue sequentially if budget remains. Drafts stay under `_work/`; canonical Markdown package files are written by the main agent. `_work/` never enters the package or ZIP.
