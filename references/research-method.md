# Research orchestration

Normalize the brief before searching. `COMPANY.md.profile_provenance.<field>` records `USER PROVIDED`, `OBSERVED`, `INFERRED` or `UNKNOWN`; observed values cite sources. Keep inferred scope separate from factual comparison cells. Unknown scalars are null and unknown lists are empty with an explanation. Never make the focal company appear more capable than its evidence allows.

Write `RESEARCH-PLAN.md` before dossier work. State the scoped market, customer/problem/offering/channel overlap criteria, direct/indirect/substitute definitions, query families, all 12 standard dimensions, industry extensions, source policy, budgets and limitations. If the focal company's domain or identity is missing, preserve the unknown and continue competitor work without matching an unrelated entity by name alone.

## Previous-run recovery

Validate the prior package before using it. Keep stable competitor IDs for verified identity matches, record aliases/redirect/local domains and parent-brand relations, and compare prior dimension gaps and evidence dates. For recovery runs, deepen and refresh the existing competitor set before expanding discovery. Carry forward previous data only as dated historical evidence with traceable origin; do not relabel its old observation date as current. `UNKNOWN` to a current observation is `newly_observed`, not proof that the business changed. A missing observation is not evidence of closure, removal or inactivity.

## Depth and source coverage

For each direct competitor, deliberately research identity, description, geography, offering, pricing, positioning, customer experience, sales channels, digital presence, trust, promotions and physical presence. Use a multi-source attempt across different relevant source types; do not set a fixed collected-source quota. One homepage cannot establish a complete dossier. Consider official homepage, product/category, price, support/policy, branch pages, plus suitable permitted public profiles, retailer/marketplace listings, directories, apps, interviews and press. Seek alternatives when an official site is restricted.

Record one `dimension_coverage` entry for each standard dimension with `state`, `source_ids`, `finding_ids`, `query_ids` and `reason`. `SUPPORTED` and `PARTIAL` require findings. `SEARCHED_UNKNOWN` requires logged targeted query IDs and a concise result note. `NOT_RESEARCHED` requires a reason and should be rare for direct competitors. `RESTRICTED` cites access metadata and explains the limitation. Add matching `research_gaps` for searched-unknown, unresearched and restricted dimensions. Never encode any of these states as a false feature value.

Discovery coverage answers how broad candidate discovery was; dossier coverage answers how much comparable evidence each subject contains. Track both. Do not pause the entire run because a few subjects have restricted evidence. A budget stop is not discovery saturation. Without a user budget, use capacity-aware limits (default ceiling 20 credible subjects, 12 relevant pages per subject, 90 minutes overall) and disclose stops. When recovering a named prior set, depth for those subjects takes priority over additional names.

Focal-company sources/findings use `competitor_id = company_id`; user facts keep their provenance. Where the focal company has no public facts, use `NOT_RESEARCHED` plus a reason and show null/unknown comparison cells. Apply the same standards to focal and competitor observations.

## Source and evidence quality

Assign each public source one `access_class` before use. Prefer primary company pages for claims about the company. If direct use is prohibited or uncertain, do not crawl that source; use alternative public profiles, directories, retailer listings, marketplaces, app listings, permitted social profiles, interviews or credible press where relevant. Clearly attribute third-party statements. Search snippets are discovery metadata, not factual evidence. Follow [source-policy](source-policy.md) and [evidence-schema](evidence-schema.md).

Create atomic findings: one entity, dimension, field, value, observation date and source set. Keep observation separate from interpretation. Normalize original-currency prices without silent currency conversion. Represent a displayed price interval with two scalar money findings and one range observation that links both endpoints. Keep the original displayed denomination in `unit`; for Iranian prices shown in toman use ISO `currency: IRR` with `unit: toman` and preserve the displayed number. Record conflict groups when sources disagree; do not select a preferred value without a dated, primary-source justification. Findings remain `needs_review`.

The main agent verifies identities and stable IDs, resolves aliases, opens cited pages, checks that each claim is supported, validates source/access metadata and dates, aligns category terminology, catches duplicate facts and prices, preserves contradictions, and removes unsupported inference. Worker drafts are not trusted automatically. Structural validity cannot prove factual truth or completeness.
