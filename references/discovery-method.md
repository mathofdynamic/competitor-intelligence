# Discovery and coverage

Scope discovery by geography, language, customer, problem, product/service category, channel and price position where relevant. Use several independent query families: category and alternate-term searches, local-language vocabulary, geography/channel searches, comparison/similar-to queries, directories, marketplaces/retailers, manufacturer directories, public profiles and reference pages. Translation-only variants do not count as independent families.

Log the actual query, language, family, geography, searched sources, results reviewed, new competitor IDs, duplicates, exclusions, date and limitations in `DISCOVERY.md`. Search snippets are discovery evidence only. Normalize brand/domain aliases, redirect and localized domains, parent/sub-brand relationships, and domains shared by unrelated businesses. Record classification reason. Keep confirmed direct competitors, candidates, indirect/substitute peers, aspirational references and excluded candidates distinct.

For a refresh or recovery run, first reconcile the previous package identity set and preserve stable IDs. Compare its coverage and evidence dates; prioritize old or weak dimensions for those competitors. Research the established set before adding newly discovered names. A changed ID needs an explicit identity reason. A previously unobserved fact becoming supported is `newly_observed`, not a business change.

Discovery coverage and dossier coverage are separate. Discovery coverage reports scope slices, query-family yields, exclusions, duplicates, deferred candidates, access limits and remaining uncertainty. Dossier coverage is a per-competitor map across every standard dimension using `SUPPORTED`, `PARTIAL`, `SEARCHED_UNKNOWN`, `NOT_RESEARCHED` or `RESTRICTED`; see `dimensions.md`. Use alternative permissible sources when an official page is restricted. A few restricted dossiers do not stop the broader run.

Do not claim all competitors globally. A practical saturation heuristic is three consecutive independent, relevant query families with no new credible identity after broad scope coverage. Reset the streak when a credible new candidate appears. Saturation describes the search process, not statistical completeness. Budget, deadline or access stops set `saturation_reached: false` and name what remains unchecked.

The validator checks the query log and, for v1.1, aggregate state counts against competitor dossiers. The main agent still judges whether query families and exclusions cover the planned market scope; structural checks cannot establish recall.
