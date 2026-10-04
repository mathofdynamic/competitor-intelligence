"""Synthetic fixture factory; never performs research or network requests."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from build_package import seal
from package_io import read_document, write_document
from validate_package import (ROOT_TYPES, DOSSIERS, ANALYSES, DIMENSIONS_V11,
                              DIMENSION_STATES, EYEWEAR_PRODUCTS)

SEED = json.loads((Path(__file__).parent / "fixtures/package-seed.json").read_text())
TIME = "2026-09-30T12:00:00Z"


def _upgrade_to_v11(root, previous_package_id=None):
    for path in root.rglob("*.md"):
        data, body = read_document(path)
        data["schema_version"] = "ci-package/v1.1"
        write_document(path, data, body)
    manifest, _ = read_document(root / "MANIFEST.md")
    package_id, run_id, generated_at = (manifest["package_id"], manifest["run_id"], manifest["generated_at"])

    def edit(rel, **fields):
        path = root / rel
        data, body = read_document(path)
        data.update(fields)
        write_document(path, data, body)
        return data

    def source(sid, source_type, url_path, access_class="DIRECT_ALLOWED"):
        evidence = f"Synthetic fixture evidence from {sid}. No public research was performed."
        blocked = access_class == "DIRECT_PROHIBITED"
        write_document(root / f"sources/{sid}.md", dict(
            schema_version="ci-package/v1.1", document_type="source", package_id=package_id,
            run_id=run_id, generated_at=generated_at, source_id=sid, competitor_id="sample-optics",
            url=f"https://sample.example.com/{url_path}", canonical_url=f"https://sample.example.com/{url_path}",
            source_type=source_type, publisher="Sample Optics", title=f"Synthetic {sid}", accessed_at=TIME,
            collection_method="manual_review", access_class=access_class,
            access_reason="Synthetic fixture policy classification.",
            restriction_scope="direct_access" if blocked else "unknown",
            reuse_mode="metadata_only" if blocked else "paraphrase_only",
            robots_status="disallowed" if blocked else "allowed",
            terms_status="reviewed_restricted" if blocked else "reviewed_allowed",
            content_sha256=hashlib.sha256((b"" if blocked else evidence.encode())).hexdigest(),
            status="blocked" if blocked else "collected", evidence_text="" if blocked else evidence),
            "# Synthetic source\n\nTest data only.\n")

    def finding(fid, dimension, field, value, sid, strength="medium", value_type="text", normalized=None,
                currency=None, unit=None):
        observed = f"Synthetic fixture observation: {field} = {value}."
        write_document(root / f"findings/{fid}.md", dict(
            schema_version="ci-package/v1.1", document_type="finding", package_id=package_id,
            run_id=run_id, generated_at=generated_at, finding_id=fid, competitor_id="sample-optics",
            dimension=dimension, field_key=field, observed_value=observed,
            normalized_value=value if normalized is None else normalized, value_type=value_type,
            currency=currency, unit=unit, observed_at=TIME, source_ids=[sid], evidence_strength=strength,
            review_status="needs_review", notes="Synthetic fixture; not a real company fact."),
            "# Synthetic finding\n\nObservation and interpretation are not conflated.\n")

    source("source-identity", "official_company", "about")
    source("source-description", "official_company", "about/overview")
    source("source-geography", "directory", "business-listing")
    source("source-offering", "official_product", "frames")
    source("source-positioning", "official_company", "brand")
    source("source-channel", "public_social", "social-profile")
    source("source-digital", "official_product", "online-store")
    source("source-promotion", "official_pricing", "shipping-promotion")
    source("source-price-two", "official_product", "frame-sample-two")
    source("source-restricted", "third_party", "terms", "DIRECT_PROHIBITED")
    old_price_finding, _ = read_document(root / "findings/finding-price.md")
    base_price = old_price_finding["normalized_value"]
    second_price = base_price + 100000
    finding("finding-identity", "identity", "brand_name", "Sample Optics", "source-identity")
    finding("finding-description", "description", "short_description", "Synthetic eyewear retailer.", "source-description")
    finding("finding-geography", "geography", "observed_region", "Tehran Province", "source-geography", "weak")
    finding("finding-offering", "offering", "product_category", "optical_frames", "source-offering", "strong")
    finding("finding-positioning", "positioning", "positioning_theme", "variety", "source-positioning")
    finding("finding-channel", "sales_channels", "channel", "ecommerce", "source-channel", "weak")
    finding("finding-digital", "digital_presence", "digital_capability", "ecommerce", "source-digital", "strong")
    finding("finding-promotion", "promotions", "promotion", "free_shipping", "source-promotion", "strong")
    finding("finding-price-two", "pricing", "visible_price", f"{second_price} IRR", "source-price-two", "strong",
            "money", second_price, "IRR", "frame")

    direct = {
        "identity": ("SUPPORTED", ["source-identity"], ["finding-identity"], [], None),
        "description": ("SUPPORTED", ["source-description"], ["finding-description"], [], None),
        "geography": ("PARTIAL", ["source-geography"], ["finding-geography"], [],
                      "One public listing gives a regional location; broader market coverage is unknown."),
        "offering": ("SUPPORTED", ["source-offering"], ["finding-offering"], [], None),
        "pricing": ("PARTIAL", ["source-price", "source-price-two"], ["finding-price", "finding-price-two"], [],
                    "Only two sampled frame prices were observed; other price tiers were not sampled."),
        "positioning": ("SUPPORTED", ["source-positioning"], ["finding-positioning"], [], None),
        "customer_experience": ("SEARCHED_UNKNOWN", [], [], ["query-cx"],
                                "Targeted public policy and help-page searches found no reliable service terms."),
        "sales_channels": ("SUPPORTED", ["source-channel"], ["finding-channel"], [], None),
        "digital_presence": ("PARTIAL", ["source-digital"], ["finding-digital"], [],
                             "Ecommerce is observed; other listed capabilities were not established."),
        "trust": ("RESTRICTED", ["source-restricted"], [], [],
                  "The source explicitly prohibits direct access; no alternate permitted source was found."),
        "promotions": ("PARTIAL", ["source-promotion"], ["finding-promotion"], ["query-promo"],
                       "One public promotion was observed; other promotion types were not assessed."),
        "physical_presence": ("NOT_RESEARCHED", [], [], [],
                              "No physical-location search was performed in this synthetic fixture.")}
    dimension_coverage = {
        dimension: {"state": state, "source_ids": sources, "finding_ids": findings,
                    "query_ids": queries, "reason": reason}
        for dimension, (state, sources, findings, queries, reason) in direct.items()
    }
    counts = {state: sum(record["state"] == state for record in dimension_coverage.values())
              for state in DIMENSION_STATES}
    supported = counts["SUPPORTED"] + counts["PARTIAL"]
    attempted = len(DIMENSIONS_V11) - counts["NOT_RESEARCHED"]
    metrics = {"coverage_counts": counts, "coverage_percentage": round(supported / 12 * 100, 2),
               "research_attempt_percentage": round(attempted / 12 * 100, 2),
               "formula": "(SUPPORTED + PARTIAL) / applicable_dimensions * 100",
               "limitations": "Evidence coverage is not competitor quality or market completeness."}
    gaps = [{"dimension": dimension, "state": state, "note": record["reason"]}
            for dimension, record in dimension_coverage.items()
            if (state := record["state"]) in {"SEARCHED_UNKNOWN", "NOT_RESEARCHED", "RESTRICTED"}]
    legacy_coverage = {dimension: {"SUPPORTED": "complete", "PARTIAL": "partial",
                                   "SEARCHED_UNKNOWN": "unknown", "NOT_RESEARCHED": "not_researched",
                                   "RESTRICTED": "limited"}[record["state"]]
                       for dimension, record in dimension_coverage.items()}

    company, _ = read_document(root / "COMPANY.md")
    company["evidence_coverage"] = {dimension: "not_researched" for dimension in DIMENSIONS_V11}
    company["dimension_coverage"] = {dimension: {"state": "NOT_RESEARCHED", "source_ids": [],
                                 "finding_ids": [], "query_ids": [],
                                 "reason": "Synthetic fixture has no supplied focal-company research."}
                                 for dimension in DIMENSIONS_V11}
    write_document(root / "COMPANY.md", company, "# Synthetic fixture\n\nTest data only.\n")

    competitor, _ = read_document(root / "COMPETITORS.md")
    entry = competitor["competitors"][0]
    entry.update(brand_name="Sample Optics", short_description="Synthetic eyewear retailer.",
                 primary_categories=["optical_frames"], evidence_coverage=legacy_coverage,
                 dimension_coverage=dimension_coverage, coverage_metrics=metrics, research_gaps=gaps,
                 identity_source_ids=["source-identity"], relevance_source_ids=["source-offering"],
                 relevance_finding_ids=["finding-offering"])
    write_document(root / "COMPETITORS.md", competitor, "# Synthetic fixture\n\nTest data only.\n")

    profile = dict(competitor_id="sample-optics", name="Sample Optics", brand_name="Sample Optics",
                   domain="sample.example.com", classification="direct", verification_status="confirmed",
                   geographies=["Iran"], primary_categories=["optical_frames"],
                   reason_for_inclusion="Synthetic customer/problem/offering/channel overlap.",
                   identity_source_ids=["source-identity"], relevance_source_ids=["source-offering"],
                   relevance_finding_ids=["finding-offering"], evidence_coverage=legacy_coverage,
                   dimension_coverage=dimension_coverage, coverage_metrics=metrics, research_gaps=gaps,
                   dimensions=["pricing"], finding_ids=["finding-price", "finding-price-two", "finding-identity",
                   "finding-description", "finding-geography", "finding-offering", "finding-positioning",
                   "finding-channel", "finding-digital", "finding-promotion"],
                   source_ids=["source-price", "source-price-two", "source-identity", "source-description",
                   "source-geography", "source-offering", "source-positioning", "source-channel", "source-digital",
                   "source-promotion"], limitations=["Synthetic fixture; no real research was performed."],
                   short_description="Synthetic eyewear retailer.",
                   business_model=None, primary_customer=None, primary_geography="Tehran Province",
                   online_presence="observed", physical_presence="unknown", sales_model=None,
                   primary_offering="optical_frames", sales_channels_observed=[
                       {"key": "ecommerce", "finding_ids": ["finding-channel"]}], trust_signals=[],
                   geography_details=[{"name": "Tehran Province", "level": "region",
                                       "finding_ids": ["finding-geography"]}],
                   logo_url="https://sample.example.com/logo.svg", favicon_url=None, brand_initials="SO",
                   brand_initials_formula="first character of each brand-name word, truncated to four characters",
                   short_description_finding_ids=["finding-description"],
                   profile_field_evidence={"brand_name": ["finding-identity"],
                       "short_description": ["finding-description"],
                       "primary_geography": ["finding-geography"], "online_presence": ["finding-digital"],
                       "primary_offering": ["finding-offering"]},
                   source_attempts=[{"source_type": "official_product", "outcome": "collected",
                                     "source_ids": ["source-price", "source-offering"],
                                     "note": "Synthetic product-page source attempt."},
                                    {"source_type": "directory", "outcome": "collected",
                                     "source_ids": ["source-geography"],
                                     "note": "Synthetic business-directory source attempt."}])
    write_document(root / "competitors/sample-optics/PROFILE.md", dict(
        schema_version="ci-package/v1.1", document_type="competitor_profile", package_id=package_id,
        run_id=run_id, generated_at=generated_at, **profile), "# Synthetic fixture\n\nTest data only.\n")

    offering = ["finding-offering"]
    edit("competitors/sample-optics/OFFERINGS.md", product_categories=[
        {"key": "optical_frames", "finding_ids": offering}], services=[])
    edit("competitors/sample-optics/PRICING.md", price_observations=[
        {"category": "optical_frames", "item_or_service": "sample frame", "amount": base_price,
         "currency": "IRR", "price_type": "visible_price", "promotion_state": "unknown",
         "observed_at": TIME, "source_ids": ["source-price"], "finding_id": "finding-price"},
        {"category": "optical_frames", "item_or_service": "second sample frame", "amount": second_price,
         "currency": "IRR", "price_type": "visible_price", "promotion_state": "unknown",
         "observed_at": TIME, "source_ids": ["source-price-two"], "finding_id": "finding-price-two"}],
        price_summaries=[{"category": "optical_frames", "currency": "IRR", "minimum_observed_price": min(base_price, second_price),
         "maximum_observed_price": max(base_price, second_price), "median_observed_price": (base_price + second_price) / 2,
         "price_observation_count": 2, "finding_ids": ["finding-price", "finding-price-two"],
         "formula": "min, max, median, count over observed prices grouped by category and currency",
         "limitations": "Two sampled products do not estimate market prices."}],
        promotions=[{"type": "free_shipping", "state": "current", "finding_ids": ["finding-promotion"]}])
    edit("competitors/sample-optics/POSITIONING.md", themes=[
        {"key": "variety", "finding_ids": ["finding-positioning"]}])
    edit("competitors/sample-optics/EXPERIENCE.md", capabilities=[])
    edit("competitors/sample-optics/DIGITAL.md", capabilities=[
        {"key": "ecommerce", "finding_ids": ["finding-digital"]}])

    queries = [
        {"query_id": "query-cx", "family": "service policies", "query": "synthetic shipping return support search",
         "language": "en", "geography": "Iran", "searched_at": TIME,
         "sources_searched": ["public product help and policy pages"], "result_urls": [],
         "new_competitor_ids": [], "duplicate_ids": [], "excluded_ids": [],
         "limitations": ["Synthetic fixture query; no network was used."]},
        {"query_id": "query-promo", "family": "promotions", "query": "synthetic free shipping promotion search",
         "language": "en", "geography": "Iran", "searched_at": TIME,
         "sources_searched": ["public pricing page"], "result_urls": ["https://sample.example.com/shipping-promotion"],
         "new_competitor_ids": [], "duplicate_ids": [], "excluded_ids": [],
         "limitations": ["Synthetic fixture query; no network was used."]}]
    counts_by_dimension = {dimension: {state: 0 for state in DIMENSION_STATES}
                           for dimension in DIMENSIONS_V11}
    for dimension, record in dimension_coverage.items():
        counts_by_dimension[dimension][record["state"]] += 1
    discovery, body = read_document(root / "DISCOVERY.md")
    discovery.update(queries=queries, coverage={
        "uncertainty": ["Synthetic fixture; discovery not executed."],
        "competitor_dimension_counts": counts_by_dimension,
        "coverage_formula": "per competitor: (SUPPORTED + PARTIAL) / 12 applicable dimensions * 100"})
    write_document(root / "DISCOVERY.md", discovery, body)
    for analysis_file, hypothesis_type in (("OPPORTUNITIES.md", "opportunity"),
                                           ("RISKS-AND-UNKNOWNS.md", "risk")):
        analysis, body = read_document(root / "analysis" / analysis_file)
        analysis["hypotheses"] = [{"id": "hypothesis-" + hypothesis_type,
            "hypothesis_id": "hypothesis-" + hypothesis_type,
            "type": hypothesis_type, "title": "Synthetic evidence-backed " + hypothesis_type,
            "summary": "Synthetic fixture only; this finding cannot support a real business decision.",
            "statement": "Synthetic fixture only; this finding cannot support a real business decision.",
            "related_competitor_ids": ["sample-optics"],
            "related_finding_ids": ["finding-offering" if hypothesis_type == "opportunity" else "finding-promotion"],
            "finding_ids": ["finding-offering" if hypothesis_type == "opportunity" else "finding-promotion"],
            "evidence_strength": "weak", "limitations": ["Synthetic fixture; no real market inference."],
            "assumptions": ["Synthetic test data only."], "counter_evidence": [],
            "suggested_validation": "Verify evidence with a human reviewer."}]
        write_document(root / "analysis" / analysis_file, analysis, body)

    run, body = read_document(root / "RUN.md")
    run.update(previous_package_id=previous_package_id,
               previous_competitor_matches=([{"previous_id": "sample-optics", "current_id": "sample-optics",
                   "match_basis": "stable fixture identity", "confidence": "strong"}]
                   if previous_package_id else []))
    write_document(root / "RUN.md", run, body)
    if previous_package_id:
        write_document(root / "analysis/CHANGELOG.md", dict(
            schema_version="ci-package/v1.1", document_type="changelog", package_id=package_id,
            run_id=run_id, generated_at=generated_at, previous_package_id=previous_package_id,
            limitations=["Synthetic fixture only; no real change assessment."],
            changes=[{"change_id": "change-new-observation", "entity_id": "sample-optics",
                      "dimension": "pricing", "field_key": "visible_price", "change_type": "newly_observed",
                      "previous_value": None, "current_value": second_price, "previous_finding_ids": [],
                      "current_finding_ids": ["finding-price-two"],
                      "interpretation": "Newly observed in this sample; not evidence of a business change.",
                      "limitations": ["Synthetic fixture."]}]), "# Synthetic changelog\n\nTest data only.\n")


def make_package(root, package_id="fixture-package", price=None, schema_version="ci-package/v1",
                 previous_package_id=None):
    seed = SEED
    cid, competitor = seed["company_id"], seed["competitor_id"]
    common = dict(schema_version="ci-package/v1", package_id=package_id,
                  run_id=package_id + "-run", generated_at=TIME)

    def emit(rel, typ, **fields):
        write_document(root / rel, dict(common, document_type=typ, **fields),
                       "# Synthetic fixture\n\nTest data only. No public research was performed.\n")

    for rel, typ in ROOT_TYPES.items():
        emit(rel, typ)
    emit("VALIDATION.md", "validation", result="WARNING", checks=[], validator="pending", hash_check="pending")
    emit("MANIFEST.md", "manifest", company_id=cid, company_name=seed["company_name"],
         created_at=TIME, research_started_at=TIME, research_finished_at=TIME,
         market_scope={"geography": "Iran", "language": "Persian", "category": "eyewear"},
         competitor_count=1, source_count=1, finding_count=1, direct_competitor_count=1,
         file_count=0, package_status="draft", generator="synthetic-test-factory", files=[])
    coverage = {dimension: "not_researched" for dimension in
                ("identity", "offering", "pricing", "positioning", "experience", "channels", "digital", "trust", "promotions")}
    coverage["pricing"] = "partial"
    profile = dict(company_id=cid, company_name=seed["company_name"], canonical_domain="example.com",
                   description="Synthetic optical retailer", industry="eyewear", sub_industries=[],
                   products_services=["frames"], target_segments=["adults"], geographies=["Iran"],
                   languages=["Persian"], sales_channels=["ecommerce"], known_price_position=None,
                   known_competitors=[], research_goals=["price comparison"], inclusions=["retail"],
                   exclusions=["wholesale"], unknowns=["price position"], evidence_coverage=coverage, finding_ids=[])
    profile["profile_provenance"] = {k: {"origin": "USER PROVIDED", "source_ids": [], "notes": "Synthetic input"}
                                     for k in profile if k not in {"company_id", "finding_ids", "evidence_coverage"}}
    emit("COMPANY.md", "company", **profile)
    emit("RUN.md", "run", research_mode="sequential", concurrency=1, budgets={"page_limit": 12},
         extension_dimensions=[], conflict_groups=[], previous_package_id=None, limitations=["Synthetic fixture"])
    emit("RESEARCH-PLAN.md", "research_plan", market_scope={"geography": "Iran"},
         criteria={"direct": "customer/problem/offering/channel overlap"}, discovery_strategy=["category", "language", "geography"],
         search_vocabulary=["frames"], dimensions=["pricing"], limitations=["Synthetic fixture"])
    emit("DISCOVERY.md", "discovery", queries=[], identity_groups=[], exclusions=[],
         coverage={"uncertainty": ["Synthetic test; discovery not executed"]},
         saturation={"rule": "three independent zero-new families", "zero_new_family_streak": 0,
                     "saturation_reached": False, "stop_reason": "fixture only"})
    entry = dict(id=competitor, name=seed["competitor_name"], domain=seed["domain"], classification="direct",
                 verification_status="confirmed", geographies=["Iran"], primary_categories=["frames"],
                 reason_for_inclusion="Synthetic overlap in customer, problem, offering and channel",
                 identity_source_ids=["source-price"], relevance_source_ids=["source-price"],
                 relevance_finding_ids=["finding-price"], evidence_coverage=coverage, last_observed_at=TIME)
    emit("COMPETITORS.md", "competitor_directory", competitors=[entry], excluded_candidates=[])
    price = seed["price"] if price is None else price
    cell = dict(entity_id=competitor, dimension="pricing", field_key="visible_price", value=price,
                unit="frame", currency="IRR", status="observed", finding_ids=["finding-price"], context="Sample frame")
    for filename, typ in DOSSIERS.items():
        if filename == "PROFILE.md":
            emit(f"competitors/{competitor}/{filename}", typ, competitor_id=competitor,
                 **{k: entry[k] for k in ("name", "domain", "classification", "verification_status", "geographies", "primary_categories", "reason_for_inclusion")},
                 evidence_coverage=coverage, identity_source_ids=entry["identity_source_ids"],
                 relevance_source_ids=entry["relevance_source_ids"], relevance_finding_ids=entry["relevance_finding_ids"],
                 dimensions=["pricing"], finding_ids=["finding-price"], limitations=["Synthetic fixture"])
        else:
            emit(f"competitors/{competitor}/{filename}", typ, competitor_id=competitor, dimensions=["pricing"],
                 finding_ids=["finding-price"], source_ids=["source-price"], rows=[cell] if filename == "PRICING.md" else [], limitations=["Synthetic fixture"])
    for filename, typ in ANALYSES.items():
        emit("analysis/" + filename, typ, dimensions=["pricing"], finding_ids=["finding-price"],
             rows=[cell] if filename in {"COMPARISON.md", "PRICING-ANALYSIS.md"} else [],
             derived_metrics=[], hypotheses=[], limitations=["Synthetic fixture"])
    evidence = f"Synthetic fixture: sample frame costs {price} IRR."
    emit("sources/source-price.md", "source", source_id="source-price", competitor_id=competitor,
         url="https://sample.example.com/frame", canonical_url="https://sample.example.com/frame",
         source_type="official_product", publisher=seed["competitor_name"], title="Synthetic frame page",
         accessed_at=TIME, collection_method="manual_review", access_class="DIRECT_ALLOWED",
         access_reason="Synthetic fixture source explicitly permits this test observation.",
         restriction_scope="unknown", reuse_mode="paraphrase_only", robots_status="allowed", terms_status="reviewed_allowed",
         content_sha256=hashlib.sha256(evidence.encode()).hexdigest(), status="collected", evidence_text=evidence)
    emit("findings/finding-price.md", "finding", finding_id="finding-price", competitor_id=competitor,
         dimension="pricing", field_key="visible_price", observed_value=evidence, normalized_value=price,
         value_type="money", currency="IRR", unit="frame", observed_at=TIME, source_ids=["source-price"],
         evidence_strength="strong", review_status="needs_review", notes="Synthetic fixture", context="Sample frame")
    if schema_version == "ci-package/v1.1":
        _upgrade_to_v11(root, previous_package_id)
    elif schema_version != "ci-package/v1":
        raise ValueError("unsupported fixture schema version")
    seal(root)
    return root
