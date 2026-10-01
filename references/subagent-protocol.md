# Bounded competitor researcher

One competitor per assignment after discovery. Default ceiling four concurrent researchers, reduced to available child slots; batch and obey aggregate host rates. RUN records research_mode (subagents/sequential), planned/actual concurrency and outcomes. Sequential fallback uses identical schemas and checks.

Each assignment supplies assignment ID, focal summary/provenance, market definition, overlap criteria, competitor identity/domain/aliases, dimensions/extensions, page/time budget, source policy, output contract and unique `_work/<id>/` destination. Pass reference content or readable paths rather than assuming inherited context.

Research only the assigned competitor. Return source/finding frontmatter records, bounded evidence, source/finding index, gaps, public citations, identity concerns, conflicts and collection failures. Draft JSON under _work is allowed; canonical output is Markdown. Every finding needs_review. Workers do not approve evidence or make market conclusions.

Main agent owns IDs and files; checks identity, links, passages, dates, terminology, currencies and comparable scope; detects duplicates/conflicts and removes unsupported claims. Drafts are not trusted automatically. On timeout salvage supported records, record gaps and retry within remaining budget or continue sequentially. Final synthesis belongs to the main agent.
