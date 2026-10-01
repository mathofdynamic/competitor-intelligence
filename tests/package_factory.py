"""Synthetic fixture factory; never performs research or network requests."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from build_package import seal
from package_io import write_document
from validate_package import ROOT_TYPES, DOSSIERS, ANALYSES

SEED = json.loads((Path(__file__).parent / "fixtures/package-seed.json").read_text())
TIME = "2026-09-30T12:00:00Z"


def make_package(root, package_id="fixture-package", price=None):
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
    profile = dict(company_id=cid, company_name=seed["company_name"], canonical_domain="example.com",
                   description="Synthetic optical retailer", industry="eyewear", sub_industries=[],
                   products_services=["frames"], target_segments=["adults"], geographies=["Iran"],
                   languages=["Persian"], sales_channels=["ecommerce"], known_price_position=None,
                   known_competitors=[], research_goals=["price comparison"], inclusions=["retail"],
                   exclusions=["wholesale"], unknowns=["price position"], finding_ids=[])
    profile["profile_provenance"] = {k: {"origin": "USER PROVIDED", "source_ids": [], "notes": "Synthetic input"}
                                     for k in profile if k not in {"company_id", "finding_ids"}}
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
                 evidence_coverage={"supported_dimensions": ["pricing"], "planned_dimensions": ["pricing"]}, last_observed_at=TIME)
    emit("COMPETITORS.md", "competitor_directory", competitors=[entry], excluded_candidates=[])
    price = seed["price"] if price is None else price
    cell = dict(entity_id=competitor, dimension="pricing", field_key="visible_price", value=price,
                unit="frame", currency="IRR", status="observed", finding_ids=["finding-price"], context="Sample frame")
    for filename, typ in DOSSIERS.items():
        if filename == "PROFILE.md":
            emit(f"competitors/{competitor}/{filename}", typ, competitor_id=competitor,
                 **{k: entry[k] for k in ("name", "domain", "classification", "verification_status", "geographies", "primary_categories", "reason_for_inclusion")},
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
         accessed_at=TIME, collection_method="manual_review", robots_status="allowed", terms_status="reviewed_allowed",
         content_sha256=hashlib.sha256(evidence.encode()).hexdigest(), status="collected", evidence_text=evidence)
    emit("findings/finding-price.md", "finding", finding_id="finding-price", competitor_id=competitor,
         dimension="pricing", field_key="visible_price", observed_value=evidence, normalized_value=price,
         value_type="money", currency="IRR", unit="frame", observed_at=TIME, source_ids=["source-price"],
         evidence_strength="strong", review_status="needs_review", notes="Synthetic fixture", context="Sample frame")
    seal(root)
    return root
