# Package v1 structured reports

All reports are scoped snapshots with dates, finding/source links and limitations. Dossiers index findings instead of repeating excerpts. Describe company-stated claims as claims.

For CI Package v1.1, populate the dossier machine fields defined in [package-contract-v1.1](package-contract-v1.1.md): a factual short description; geography and physical-presence evidence; product/service taxonomy; observed original-currency price samples and transparent summaries; claimed positioning themes; experience, channel, digital and trust capabilities; promotions; exact per-dimension research states; coverage percentages/counts; and research gaps. A dossier page should explain the evidence and limitations in its body, while the importer reads the structured records. If research found no reliable value, show its specific state rather than leaving a blank panel.

| Analysis | Content |
| --- | --- |
| EXECUTIVE-SUMMARY | goals, landscape, material observations, coverage, unknowns |
| MARKET-MAP | classes, customer/category/geography overlap, confirmed/candidate |
| COMPARISON | focal and competitor cells on matched dimensions |
| OFFERING-MATRIX | categories/capabilities, unknown/conflict states |
| PRICING-ANALYSIS | sampled ranges, currencies/units/periods, match rules |
| POSITIONING | stated claims, patterns, attribution |
| CUSTOMER-EXPERIENCE | public delivery/returns/warranty/support/customization |
| DIGITAL-PRESENCE | observed channels/resources/conversion mechanisms |
| OPPORTUNITIES | evidence-backed hypotheses, alternatives, validation |
| RISKS-AND-UNKNOWNS | gaps/conflicts, blocked sources, uncertain identity |

All analysis frontmatter contains dimensions, finding_ids, rows, derived_metrics, hypotheses, limitations; unused lists empty. Cells: entity_id, dimension, field_key, value (scalar/null), unit, currency, status (observed, user_provided, unknown, not_researched, conflict), finding_ids, provenance for supplied focal facts, context. `observed_absent` is a boolean false backed by a finding, never an empty cell. Chart import reads cells, not prose. Unknown/not_researched/conflict has null value; missing evidence is never zero.

Metrics supply formula, finding inputs, units and limitations. Hypotheses: hypothesis_id, statement, finding_ids, assumptions, counter_evidence, limitations, suggested_validation. No overall scores/winners. Market share is unknown without explicit credible scoped evidence; never derive it from website observations.

V1.1 opportunity/risk hypotheses also identify type, title, summary, related competitor IDs, related finding IDs and evidence strength. Phrase them as evidence-backed hypotheses and list counter-evidence or the next validation step where applicable. Do not invent financial impact or guarantee a business result.

The following historical publication format concerns approved legacy application reports, not Package v1 research drafts.

# Legacy report format

Reports are scoped snapshots, not permanent truth. Start with company, market, categories, observation window, source count, finding count and limitations.

For every published price or specification include:

- finding ID and version
- subject and category
- exact source URL
- observation date and local context
- observed text
- normalized value, currency and unit when applicable
- reviewer decision and reviewer note
- confidence and limitations

If evidence is missing, say `unknown`. Do not replace it with an estimate. Do not publish rankings, market-share percentages or broad competitive conclusions unless the report brief, denominator and approved evidence support them.
