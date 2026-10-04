"""Validate CI Package v1/v1.1 offline. Exit 1 on FAIL; never approve evidence."""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import math
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from package_io import digest, portable_path, read_document, write_document
from schema_check import frontmatter_errors

ROOT_TYPES = {"MANIFEST.md": "manifest", "COMPANY.md": "company", "RUN.md": "run",
              "DISCOVERY.md": "discovery", "COMPETITORS.md": "competitor_directory",
              "VALIDATION.md": "validation", "RESEARCH-PLAN.md": "research_plan"}
DOSSIERS = {name + ".md": "competitor_" + name.lower() for name in
            ("PROFILE", "OFFERINGS", "PRICING", "POSITIONING", "EXPERIENCE", "DIGITAL", "EVIDENCE")}
ANALYSES = {name + ".md": "analysis" for name in (
    "EXECUTIVE-SUMMARY", "MARKET-MAP", "COMPARISON", "OFFERING-MATRIX", "PRICING-ANALYSIS",
    "POSITIONING", "CUSTOMER-EXPERIENCE", "DIGITAL-PRESENCE", "OPPORTUNITIES", "RISKS-AND-UNKNOWNS")}
DIMENSIONS = {"identity", "offering", "pricing", "positioning", "experience", "channels",
              "digital", "trust", "promotions"}
DIMENSIONS_V11 = {"identity", "description", "geography", "offering", "pricing", "positioning",
                  "customer_experience", "sales_channels", "digital_presence", "trust", "promotions",
                  "physical_presence"}
SUPPORTED_SCHEMA_VERSIONS = {"ci-package/v1", "ci-package/v1.1"}
DIMENSION_STATES = {"SUPPORTED", "PARTIAL", "SEARCHED_UNKNOWN", "NOT_RESEARCHED", "RESTRICTED"}
EYEWEAR_PRODUCTS = {"prescription_frames", "sunglasses", "optical_frames", "blue_light_glasses",
                    "contact_lenses", "optical_lenses", "children_eyewear", "sports_eyewear",
                    "reading_glasses", "accessories"}
EYEWEAR_SERVICES = {"eye_exam", "optometry", "prescription_service", "prescription_upload",
                    "frame_fitting", "lens_fitting", "repair", "customization", "consultation",
                    "virtual_try_on"}
POSITIONING_THEMES = {"affordability", "premium", "fashion_design", "medical_expertise", "quality",
                      "variety", "convenience", "speed", "customization", "digital_convenience",
                      "physical_expertise", "family", "children", "professional_optics"}
SALES_CHANNELS = {"ecommerce", "physical_store", "instagram_social", "marketplace", "phone",
                  "messaging", "b2b", "online_appointment", "in_person"}
DIGITAL_CAPABILITIES = {"ecommerce", "mobile_app", "virtual_try_on", "prescription_upload",
                        "online_consultation", "online_booking", "blog_content", "guides",
                        "product_filters", "online_support", "social_presence"}
EXPERIENCE_CAPABILITIES = {"shipping", "delivery", "returns", "exchange", "warranty", "support",
                           "consultation", "fitting", "order_tracking", "after_sales", "physical_service",
                           "appointment"}
TRUST_SIGNALS = {"warranty", "return_policy", "guarantee", "professional_credentials", "certifications",
                 "physical_presence", "review_mechanism", "expert_claim", "optometry_presence"}
PROMOTION_TYPES = {"percentage_discount", "fixed_discount", "coupon", "bundle", "loyalty", "referral",
                   "free_shipping", "installments", "seasonal_campaign"}
SOURCE_ACCESS_CLASSES = {"DIRECT_ALLOWED", "DISCOVERY_ONLY", "DIRECT_PROHIBITED", "UNKNOWN"}
RESTRICTION_SCOPES = {"direct_access", "content_reuse", "commercial_reuse", "other", "unknown"}
REUSE_MODES = {"paraphrase_only", "short_quote", "metadata_only", "none"}
COVERAGE_BANDS = {"complete", "good", "partial", "limited", "unknown", "not_researched"}
CLASSIFICATIONS = {"direct", "indirect", "substitute", "aspirational/reference", "excluded"}
ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,119}\Z")
HASH = re.compile(r"[a-f0-9]{64}\Z")


def public_url(value):
    if not isinstance(value, str) or any(c.isspace() for c in value):
        return False
    try:
        u = urlsplit(value)
        if u.scheme not in {"https", "http"} or not u.hostname or u.username or u.password:
            return False
        if u.port not in {None, 80, 443}:
            return False
        host = u.hostname.lower()
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return ("." in host and not re.fullmatch(r"[0-9.]+", host)
                    and not host.endswith((".local", ".localhost", ".internal"))
                    and all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", s)
                            for s in host.split(".")))
    except ValueError:
        return False


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamps must be quoted ISO-8601 strings")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    return dt


def canonical_domain(value):
    return (isinstance(value, str) and value == value.lower()
            and bool(re.fullmatch(r"[a-z0-9.-]+", value))
            and public_url("https://" + value))


def expected_type(path):
    parts = path.split("/")
    if len(parts) == 1:
        return ROOT_TYPES.get(path)
    if len(parts) == 2 and parts[0] == "analysis":
        return "changelog" if parts[1] == "CHANGELOG.md" else ANALYSES.get(parts[1])
    if len(parts) == 3 and parts[0] == "competitors":
        return DOSSIERS.get(parts[2])
    if len(parts) == 2 and parts[0] in {"sources", "findings"} and parts[1].endswith(".md"):
        return "source" if parts[0] == "sources" else "finding"
    return None


def _validate(root: Path, check_hashes=True):
    issues = []
    records = {}

    def check(ok, path, message, severity="FAIL"):
        if not ok:
            issues.append({"status": severity, "path": path, "message": message})

    if not root.is_dir() or root.is_symlink() or (hasattr(root, "is_junction") and root.is_junction()):
        return [{"status": "FAIL", "path": str(root), "message": "package must be a real directory"}], {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        linked = p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction())
        check(not linked and p.resolve().is_relative_to(root.resolve()), rel, "symlink/junction or escaped path forbidden")
        if linked or not p.resolve().is_relative_to(root.resolve()):
            continue
        check(portable_path(rel), rel, "unsafe/nonportable path")
        if p.is_dir():
            check(rel in {"analysis", "sources", "findings", "competitors"}
                  or (rel.startswith("competitors/") and len(rel.split("/")) == 2),
                  rel, "directory outside contract")
            continue
        typ = expected_type(rel)
        check(typ is not None, rel, "file outside contract")
        if typ is None:
            continue
        try:
            d, body = read_document(p)
            records[rel] = d
            for error in frontmatter_errors(d):
                check(False, rel, error)
            check(d.get("document_type") == typ, rel, "document_type does not match path")
            for field in ("schema_version", "document_type", "package_id", "run_id", "generated_at"):
                check(field in d and d[field] not in (None, ""), rel, "missing " + field)
            check(d.get("schema_version") in SUPPORTED_SCHEMA_VERSIONS, rel, "unsupported schema version")
            for field in ("package_id", "run_id"):
                check(isinstance(d.get(field), str) and bool(ID.fullmatch(d[field])), rel, "invalid " + field)
            try:
                check(timestamp(d.get("generated_at")) <= datetime.now(timezone.utc), rel, "future generated_at")
            except (ValueError, TypeError):
                check(False, rel, "invalid generated_at")
            check(bool(body.strip()), rel, "empty explanation")
        except Exception as exc:
            check(False, rel, "invalid document: " + str(exc))
    for rel in [*ROOT_TYPES, *("analysis/" + n for n in ANALYSES)]:
        check(rel in records, rel, "required file missing")
    manifest = records.get("MANIFEST.md", {})
    package_version = manifest.get("schema_version")
    check(all(d.get("schema_version") == package_version for d in records.values()),
          "MANIFEST.md", "all records must use the same schema version")
    declared_dimensions = (DIMENSIONS_V11 if package_version == "ci-package/v1.1" else DIMENSIONS)
    declared_dimensions = declared_dimensions | set(records.get("RUN.md", {}).get("extension_dimensions", []))
    report = records.get("VALIDATION.md", {})
    if check_hashes:
        check(report.get("result") != "FAIL" or manifest.get("package_status") != "import_ready",
              "VALIDATION.md", "failed package cannot be import_ready")
    for rel, d in records.items():
        for key in ("package_id", "run_id"):
            check(d.get(key) == manifest.get(key), rel, "inconsistent " + key)
    for key in ("company_id", "company_name", "created_at", "research_started_at",
                "research_finished_at", "market_scope", "competitor_count", "source_count",
                "finding_count", "direct_competitor_count", "package_status", "generator", "file_count", "files"):
        check(key in manifest, "MANIFEST.md", "missing " + key)
    check(manifest.get("package_status") in {"draft", "review_ready", "import_ready"},
          "MANIFEST.md", "invalid package_status")
    try:
        start, finish, created = [timestamp(manifest.get(k)) for k in
                                  ("research_started_at", "research_finished_at", "created_at")]
        check(start <= finish <= created <= datetime.now(timezone.utc), "MANIFEST.md", "invalid research date order")
    except (ValueError, TypeError):
        check(False, "MANIFEST.md", "invalid research timestamps")
    entries = manifest.get("files", [])
    check(isinstance(entries, list), "MANIFEST.md", "files must be a list")
    listed, folded = set(), set()
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            check(False, "MANIFEST.md", "invalid file entry")
            continue
        rel = entry.get("path")
        if not portable_path(rel):
            check(False, "MANIFEST.md", "unsafe manifest path")
            continue
        check(rel.casefold() not in folded, rel, "duplicate/case-colliding manifest path")
        listed.add(rel)
        folded.add(rel.casefold())
        check(rel in records, rel, "manifest file missing or invalid")
        check(entry.get("document_type") == expected_type(rel), rel, "manifest document_type mismatch")
        check(isinstance(entry.get("sha256"), str) and bool(HASH.fullmatch(entry["sha256"])), rel, "invalid SHA-256")
        if rel in records and check_hashes:
            check(entry.get("sha256") == digest(root / rel), rel, "hash mismatch")
    check(listed == set(records), "MANIFEST.md", "manifest inventory mismatch")
    directory = records.get("COMPETITORS.md", {})
    competitors = directory.get("competitors", [])
    check(isinstance(competitors, list), "COMPETITORS.md", "competitors must be a list")
    entities = {manifest.get("company_id")}
    seen = set()
    domains = set()
    included = []
    for c in competitors if isinstance(competitors, list) else []:
        if not isinstance(c, dict):
            check(False, "COMPETITORS.md", "invalid competitor record")
            continue
        cid = c.get("id")
        check(isinstance(cid, str) and bool(ID.fullmatch(cid)), "COMPETITORS.md", "invalid competitor ID")
        if not isinstance(cid, str):
            continue
        check(cid not in seen and cid not in entities, "COMPETITORS.md", "duplicate competitor ID")
        seen.add(cid)
        check(c.get("classification") in CLASSIFICATIONS, cid, "invalid classification")
        check(c.get("verification_status") in {"confirmed", "candidate"}, cid, "invalid verification_status")
        for field in ("name", "domain", "geographies", "primary_categories", "reason_for_inclusion",
                      "identity_source_ids", "relevance_source_ids", "relevance_finding_ids",
                      "evidence_coverage", "last_observed_at"):
            check(field in c, cid, "missing " + field)
        coverage = c.get("evidence_coverage")
        check(isinstance(coverage, dict) and set(coverage) == declared_dimensions, cid,
              "evidence_coverage must classify every declared dimension")
        if isinstance(coverage, dict):
            check(all(value in COVERAGE_BANDS for value in coverage.values()), cid,
                  "invalid evidence coverage band")
        check(canonical_domain(c.get("domain")), cid, "invalid domain")
        domain = str(c.get("domain", "")).lower()
        check(domain not in domains, cid, "duplicate canonical domain requires identity reconciliation")
        domains.add(domain)
        try:
            check(timestamp(c.get("last_observed_at")) <= finish, cid, "competitor observation outside run")
        except (ValueError, TypeError, UnboundLocalError):
            check(False, cid, "invalid last_observed_at")
        if c.get("classification") != "excluded":
            entities.add(cid)
            included.append(c)
            for filename in DOSSIERS:
                rel = f"competitors/{cid}/{filename}"
                check(rel in records and records[rel].get("competitor_id") == cid, rel, "missing/mismatched dossier")
            profile = records.get(f"competitors/{cid}/PROFILE.md", {})
            for field in ("name", "domain", "classification", "verification_status"):
                check(profile.get(field) == c.get(field), cid, "profile/directory identity mismatch: " + field)
    for c in directory.get("excluded_candidates", []):
        if not isinstance(c, dict):
            continue
        cid = c.get("id")
        check(isinstance(cid, str) and bool(ID.fullmatch(cid)), "COMPETITORS.md", "invalid excluded ID")
        if isinstance(cid, str):
            check(cid not in seen and cid not in entities, "COMPETITORS.md", "duplicate excluded ID")
            seen.add(cid)
    company = records.get("COMPANY.md", {})
    check(company.get("company_id") == manifest.get("company_id"), "COMPANY.md", "company identity mismatch")
    for key in ("company_name", "canonical_domain", "description", "industry", "sub_industries",
                "products_services", "target_segments", "geographies", "languages", "sales_channels",
                "known_price_position", "known_competitors", "research_goals", "inclusions", "exclusions",
                "unknowns", "evidence_coverage", "profile_provenance", "finding_ids"):
        check(key in company, "COMPANY.md", "missing " + key)
    check(isinstance(manifest.get("company_id"), str) and bool(ID.fullmatch(manifest["company_id"])),
          "MANIFEST.md", "invalid company ID")
    check(company.get("canonical_domain") is None or canonical_domain(company.get("canonical_domain")),
          "COMPANY.md", "invalid canonical domain")
    for key, provenance in company.get("profile_provenance", {}).items():
        check(isinstance(provenance, dict) and provenance.get("origin") in
              {"USER PROVIDED", "OBSERVED", "INFERRED", "UNKNOWN"}, "COMPANY.md", "invalid provenance: " + key)
        if isinstance(provenance, dict):
            check(provenance.get("origin") != "OBSERVED" or bool(provenance.get("source_ids")),
                  "COMPANY.md", "observed company field requires evidence")
    comparable_company_fields = ("company_name", "canonical_domain", "description", "industry", "sub_industries",
                                 "products_services", "target_segments", "geographies", "languages", "sales_channels",
                                 "known_price_position", "known_competitors", "research_goals", "inclusions", "exclusions", "unknowns")
    for field in comparable_company_fields:
        check(field in company.get("profile_provenance", {}), "COMPANY.md", "missing field provenance: " + field)
    company_coverage = company.get("evidence_coverage")
    check(isinstance(company_coverage, dict) and set(company_coverage) == declared_dimensions,
          "COMPANY.md", "evidence_coverage must classify every declared dimension")
    if isinstance(company_coverage, dict):
        check(all(value in COVERAGE_BANDS for value in company_coverage.values()), "COMPANY.md",
              "invalid evidence coverage band")
    if package_version == "ci-package/v1.1":
        focal_coverage = company.get("dimension_coverage")
        check(isinstance(focal_coverage, dict) and set(focal_coverage) == DIMENSIONS_V11,
              "COMPANY.md", "v1.1 company dimension_coverage must contain all 12 standard dimensions")
        for dimension, item in focal_coverage.items() if isinstance(focal_coverage, dict) else []:
            check(isinstance(item, dict) and item.get("state") in DIMENSION_STATES,
                  "COMPANY.md", "invalid company dimension state: " + str(dimension))
            if isinstance(item, dict) and item.get("state") == "NOT_RESEARCHED":
                check(bool(item.get("reason")), "COMPANY.md", "unresearched company dimension requires a reason")
    sources, findings = {}, {}
    for rel, d in records.items():
        typ = d.get("document_type")
        if typ not in {"source", "finding"}:
            continue
        key = "source_id" if typ == "source" else "finding_id"
        rid = d.get(key)
        target = sources if typ == "source" else findings
        check(isinstance(rid, str) and bool(ID.fullmatch(rid)), rel, "invalid record ID")
        if not isinstance(rid, str):
            continue
        check(rid not in target, rel, "duplicate " + key)
        target[rid] = d
        check(Path(rel).stem == rid, rel, "filename/ID mismatch")
        check(d.get("competitor_id") in entities, rel, "broken competitor reference")
        if typ == "source":
            for field in ("url", "canonical_url", "source_type", "publisher", "title", "accessed_at",
                          "collection_method", "access_class", "access_reason", "restriction_scope", "reuse_mode",
                          "robots_status", "terms_status", "content_sha256", "status", "evidence_text"):
                check(field in d, rel, "missing " + field)
            for field in ("url", "canonical_url"):
                check(public_url(d.get(field)), rel, "invalid public " + field)
            check(d.get("source_type") in {"official_product", "official_pricing", "official_docs", "official_company",
                  "official_press", "public_social", "retailer", "marketplace", "directory", "third_party", "search_snippet"}, rel, "invalid source_type")
            check(d.get("collection_method") in {"browser_public", "http_public", "manual_review", "public_search"}, rel, "invalid collection method")
            check(d.get("robots_status") in {"allowed", "disallowed", "unknown"}, rel, "invalid robots_status")
            check(d.get("terms_status") in {"reviewed_allowed", "reviewed_restricted", "unknown"}, rel, "invalid terms_status")
            check(d.get("status") in {"collected", "blocked", "unverified", "stale"}, rel, "invalid source status")
            access_class = d.get("access_class")
            restriction_scope = d.get("restriction_scope")
            reuse_mode = d.get("reuse_mode")
            check(access_class in SOURCE_ACCESS_CLASSES, rel, "invalid access_class")
            check(restriction_scope in RESTRICTION_SCOPES, rel, "invalid restriction_scope")
            check(reuse_mode in REUSE_MODES, rel, "invalid reuse_mode")
            check(isinstance(d.get("access_reason"), str) and bool(d["access_reason"].strip()), rel,
                  "access_reason is required")
            if d.get("policy_url") is not None:
                check(public_url(d.get("policy_url")), rel, "invalid public policy_url")
            evidence = d.get("evidence_text")
            check(isinstance(evidence, str) and len(evidence) <= 4000, rel, "bounded evidence_text required")
            if isinstance(evidence, str):
                check(d.get("content_sha256") == hashlib.sha256(evidence.encode("utf-8")).hexdigest(), rel, "content hash mismatch")
            if access_class == "DIRECT_ALLOWED":
                restricted_scope_ok = d.get("terms_status") != "reviewed_restricted" or restriction_scope in {"content_reuse", "commercial_reuse", "other"}
                check(d.get("status") == "collected" and d.get("robots_status") == "allowed" and
                      restricted_scope_ok and reuse_mode == "paraphrase_only" and bool(evidence), rel,
                      "DIRECT_ALLOWED requires public access, no explicit direct-access prohibition, and bounded paraphrased evidence")
            elif access_class == "DISCOVERY_ONLY":
                check(reuse_mode == "metadata_only" and evidence == "", rel,
                      "DISCOVERY_ONLY must retain metadata only, without source content")
                check(d.get("status") in {"collected", "unverified"}, rel,
                      "DISCOVERY_ONLY must not be represented as a blocked research fetch")
            elif access_class == "DIRECT_PROHIBITED":
                check(d.get("status") == "blocked" and evidence == "" and
                      reuse_mode in {"metadata_only", "none"} and restriction_scope == "direct_access", rel,
                      "DIRECT_PROHIBITED must not contain fetched content")
            elif access_class == "UNKNOWN":
                check(d.get("status") in {"unverified", "blocked"} and evidence == "" and
                      reuse_mode in {"metadata_only", "none"}, rel,
                      "UNKNOWN access cannot carry collected content")
            if d.get("source_type") == "search_snippet":
                check(access_class == "DISCOVERY_ONLY" and evidence == "", rel,
                      "search snippets are metadata-only discovery sources")
            try:
                accessed = timestamp(d.get("accessed_at"))
                check(start <= accessed <= finish, rel, "source date outside run")
            except (ValueError, TypeError, UnboundLocalError):
                check(False, rel, "invalid source date")
        else:
            for field in ("dimension", "field_key", "observed_value", "value_type", "observed_at", "source_ids", "evidence_strength", "review_status", "notes"):
                check(field in d, rel, "missing " + field)
            check(d.get("review_status") == "needs_review", rel, "agent findings must need review")
            check(d.get("dimension") in declared_dimensions, rel, "unsupported dimension")
            check(d.get("evidence_strength") in {"strong", "medium", "weak"}, rel, "invalid evidence strength")
            check(isinstance(d.get("observed_value"), (str, int, float, bool)) and d.get("observed_value") != "", rel, "atomic observation required")
            vt = d.get("value_type")
            value = d.get("normalized_value", d.get("observed_value"))
            numeric = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
            check(vt in {"text", "number", "integer", "boolean", "money"}, rel, "unsupported value_type")
            check((vt == "text" and isinstance(value, str)) or (vt == "boolean" and isinstance(value, bool)) or
                  (vt in {"number", "money"} and numeric) or (vt == "integer" and isinstance(value, int) and not isinstance(value, bool)), rel, "value_type mismatch")
            if vt == "money":
                currencies = (Path(__file__).parent.parent / "schemas/currencies.txt").read_text().split()
                check(d.get("currency") in currencies, rel, "invalid ISO-4217 currency")
                check(numeric and value >= 0, rel, "invalid monetary value")
                check(bool(d.get("unit")), rel, "money requires unit")
            try:
                observed = timestamp(d.get("observed_at"))
                check(start <= observed <= finish, rel, "observation date outside run")
            except (ValueError, TypeError, UnboundLocalError):
                check(False, rel, "invalid observation date")
    for competitor in included:
        cid = competitor.get("id")
        identity_ids = competitor.get("identity_source_ids")
        relevance_ids = competitor.get("relevance_source_ids")
        relevance_finding_ids = competitor.get("relevance_finding_ids")
        check(isinstance(identity_ids, list) and bool(identity_ids), str(cid),
              "competitor requires identity source IDs")
        check(isinstance(relevance_ids, list) and bool(relevance_ids), str(cid),
              "competitor requires relevance source IDs")
        check(isinstance(relevance_finding_ids, list), str(cid), "relevance_finding_ids must be a list")
        for source_id in (identity_ids or []) + (relevance_ids or []) if isinstance(identity_ids, list) and isinstance(relevance_ids, list) else []:
            source = sources.get(source_id)
            check(source is not None, str(cid), "competitor source reference is missing: " + str(source_id))
            if source:
                check(source.get("competitor_id") == cid, str(cid), "competitor source belongs to another entity")
                check(source.get("access_class") in {"DIRECT_ALLOWED", "DISCOVERY_ONLY"}, str(cid),
                      "prohibited or unknown source cannot establish competitor identity/relevance")
        for finding_id in relevance_finding_ids if isinstance(relevance_finding_ids, list) else []:
            finding = findings.get(finding_id)
            check(finding is not None and finding.get("competitor_id") == cid, str(cid),
                  "competitor relevance finding is missing or belongs to another entity")
            if finding:
                check(bool(set(finding.get("source_ids", [])) & set(relevance_ids or [])), str(cid),
                      "relevance finding must cite a listed relevance source")
        direct_relevance = [sources[sid] for sid in relevance_ids if sid in sources and
                            sources[sid].get("access_class") == "DIRECT_ALLOWED"] if isinstance(relevance_ids, list) else []
        if competitor.get("verification_status") == "confirmed":
            check(bool(direct_relevance) and bool(relevance_finding_ids), str(cid),
                  "confirmed competitor requires a DIRECT_ALLOWED relevance finding")
        profile = records.get(f"competitors/{cid}/PROFILE.md", {})
        check(profile.get("evidence_coverage") == competitor.get("evidence_coverage"), str(cid),
              "profile/directory evidence_coverage mismatch")
    for fid, f in findings.items():
        check(fid not in sources, fid, "duplicate ID across source/finding records")
        refs = f.get("source_ids")
        check(isinstance(refs, list) and bool(refs) and all(isinstance(s, str) for s in refs), fid, "finding requires source IDs")
        for sid in refs if isinstance(refs, list) else []:
            if not isinstance(sid, str):
                continue
            s = sources.get(sid)
            check(s is not None, fid, "broken source reference: " + sid)
            if s:
                check(s.get("competitor_id") == f.get("competitor_id"), fid, "source belongs to another entity")
                check(s.get("access_class") == "DIRECT_ALLOWED" and s.get("status") == "collected" and
                      s.get("source_type") != "search_snippet" and bool(s.get("evidence_text")), fid,
                      "source cannot support a factual finding")
                check(f.get("evidence_strength") == "weak" or s.get("source_type", "").startswith("official_"), fid, "non-primary claim must be weak")
                check(f.get("evidence_strength") != "strong" or s.get("source_type") in {"official_product", "official_pricing"}, fid, "strong evidence requires direct official page")
    for rel, d in records.items():
        for field, index in (("source_ids", sources), ("finding_ids", findings)):
            refs = d.get(field, [])
            check(isinstance(refs, list), rel, field + " must be a list")
            for rid in refs if isinstance(refs, list) else []:
                check(isinstance(rid, str) and rid in index, rel, "broken " + field)
        if rel.startswith("competitors/"):
            check(d.get("competitor_id") in entities, rel, "broken dossier identity")
        for metric in d.get("derived_metrics", []):
            check(isinstance(metric, dict) and all(metric.get(k) for k in ("field_key", "formula", "inputs", "limitations")), rel, "derived metric lacks formula, inputs or limitations")
        for cell in d.get("rows", []):
            if not isinstance(cell, dict):
                continue
            check(cell.get("entity_id") in entities, rel, "cell has broken entity reference")
            check(cell.get("dimension") in declared_dimensions, rel, "cell has unsupported dimension")
            refs = cell.get("finding_ids", [])
            for fid in refs if isinstance(refs, list) else []:
                check(isinstance(fid, str) and fid in findings and findings[fid].get("competitor_id") == cell.get("entity_id"), rel, "cell has broken/cross-entity evidence")
                if isinstance(fid, str) and fid in findings:
                    linked = findings[fid]
                    check(linked.get("dimension") == cell.get("dimension") and linked.get("field_key") == cell.get("field_key"), rel, "cell evidence belongs to another field")
                    check(not linked.get("conflict_group_id") or cell.get("status") == "conflict", rel, "conflicting finding cannot become a resolved chart value")
            state = cell.get("status")
            check(state in {"observed", "user_provided", "unknown", "not_researched", "conflict"}, rel,
                  "invalid analytical cell status")
            check(state not in {"unknown", "conflict"} or cell.get("value") is None, rel, "unknown/conflict chart value must be null")
            check(state != "observed" or bool(refs), rel, "observed chart value requires evidence")
            check(state != "user_provided" or (cell.get("entity_id") == manifest.get("company_id") and
                  cell.get("provenance") == "USER PROVIDED"), rel, "invalid supplied company value")
            check(state != "conflict" or (isinstance(refs, list) and len(refs) >= 2), rel, "conflict cell requires both observations")
            if state == "observed" and isinstance(refs, list) and len(refs) == 1 and refs[0] in findings:
                linked = findings[refs[0]]
                check(cell.get("value") == linked.get("normalized_value", linked.get("observed_value")), rel, "chart value contradicts evidence")
                check(cell.get("currency") == linked.get("currency") and cell.get("unit") == linked.get("unit"), rel, "chart units contradict evidence")
        for metric in d.get("derived_metrics", []):
            if isinstance(metric, dict):
                check(metric.get("entity_id") in entities, rel, "metric has broken entity reference")
                for fid in metric.get("inputs", []):
                    check(isinstance(fid, str) and fid in findings, rel, "metric input finding missing")
        for hypothesis in d.get("hypotheses", []):
            if isinstance(hypothesis, dict):
                for fid in hypothesis.get("finding_ids", []):
                    check(isinstance(fid, str) and fid in findings, rel, "hypothesis evidence missing")
    for key, provenance in company.get("profile_provenance", {}).items():
        if isinstance(provenance, dict):
            for sid in provenance.get("source_ids", []):
                check(isinstance(sid, str) and sid in sources and sources[sid].get("competitor_id") == manifest.get("company_id"), "COMPANY.md", "broken company provenance source")
    groups = records.get("RUN.md", {}).get("conflict_groups", [])
    group_ids = set()
    for group in groups:
        if not isinstance(group, dict):
            check(False, "RUN.md", "invalid conflict group")
            continue
        gid = group.get("conflict_group_id")
        check(isinstance(gid, str) and gid not in group_ids, "RUN.md", "duplicate/invalid conflict ID")
        if isinstance(gid, str):
            group_ids.add(gid)
        members = group.get("finding_ids", [])
        check(isinstance(members, list) and len(members) >= 2 and bool(group.get("interpretation")), "RUN.md", "incomplete conflict group")
        for fid in members if isinstance(members, list) else []:
            check(isinstance(fid, str) and fid in findings and findings[fid].get("conflict_group_id") == gid, "RUN.md", "broken conflict membership")
        valid_members = [findings[fid] for fid in members if isinstance(fid, str) and fid in findings]
        contexts = {(f.get("competitor_id"), f.get("dimension"), f.get("field_key")) for f in valid_members}
        check(len(contexts) <= 1, "RUN.md", "conflict members must share entity and field")
        if group.get("preferred_finding_id"):
            check(group["preferred_finding_id"] in members and bool(group.get("justification")), "RUN.md", "conflict preference needs member and justification")
        check(False, "RUN.md", "unresolved evidence conflict: " + str(gid), "WARNING")
    for fid, f in findings.items():
        check(not f.get("conflict_group_id") or f["conflict_group_id"] in group_ids, fid, "missing conflict group")
    previous = records.get("RUN.md", {}).get("previous_package_id")
    check(bool(previous) == ("analysis/CHANGELOG.md" in records), "RUN.md", "changelog/previous-run mismatch")
    if package_version == "ci-package/v1.1":
        matches = records.get("RUN.md", {}).get("previous_competitor_matches", [])
        check(isinstance(matches, list), "RUN.md", "previous_competitor_matches must be a list")
        previous_ids, current_ids = set(), set()
        current_included_ids = {c.get("id") for c in included}
        for match in matches if isinstance(matches, list) else []:
            if not isinstance(match, dict):
                check(False, "RUN.md", "previous competitor match must be an object")
                continue
            old_id, current_id = match.get("previous_id"), match.get("current_id")
            check(isinstance(old_id, str) and bool(ID.fullmatch(old_id)) and
                  isinstance(current_id, str) and current_id in current_included_ids, "RUN.md",
                  "previous competitor match has an invalid or unknown identity")
            check(old_id not in previous_ids and current_id not in current_ids, "RUN.md",
                  "duplicate previous/current competitor match")
            previous_ids.add(old_id)
            current_ids.add(current_id)
            check(old_id == current_id, "RUN.md",
                  "matched prior competitors must retain their stable competitor ID")
            check(bool(match.get("match_basis")) and match.get("confidence") in {"strong", "medium", "weak"},
                  "RUN.md", "previous competitor match requires a basis and evidence strength")
        if previous:
            check(bool(matches), "RUN.md", "prior package requires explicit competitor identity matching")
        else:
            check(not matches, "RUN.md", "identity matches cannot exist without a previous package")
    if previous:
        changes = records.get("analysis/CHANGELOG.md", {})
        check(changes.get("previous_package_id") == previous and isinstance(changes.get("changes"), list), "analysis/CHANGELOG.md", "invalid change tracking")
        change_ids = set()
        for change in changes.get("changes", []):
            change_id = change.get("change_id")
            check(isinstance(change_id, str) and change_id not in change_ids, "analysis/CHANGELOG.md", "duplicate/invalid change ID")
            if isinstance(change_id, str):
                change_ids.add(change_id)
            for fid in change.get("current_finding_ids", []):
                check(isinstance(fid, str) and fid in findings, "analysis/CHANGELOG.md", "broken current change finding")
    discovery = records.get("DISCOVERY.md", {})
    queries = discovery.get("queries", [])
    query_ids = set()
    for query in queries:
        for key in ("query_id", "family", "query", "language", "geography", "searched_at", "sources_searched",
                    "result_urls", "new_competitor_ids", "duplicate_ids", "excluded_ids", "limitations"):
            check(key in query, "DISCOVERY.md", "query missing " + key)
        qid = query.get("query_id")
        check(isinstance(qid, str) and qid not in query_ids, "DISCOVERY.md", "duplicate/invalid query ID")
        if isinstance(qid, str):
            query_ids.add(qid)
        for url in query.get("result_urls", []):
            check(public_url(url), "DISCOVERY.md", "invalid discovery URL")
        for key in ("new_competitor_ids", "duplicate_ids", "excluded_ids"):
            for cid in query.get(key, []):
                check(cid in seen, "DISCOVERY.md", "broken discovery identity reference")
        try:
            check(start <= timestamp(query.get("searched_at")) <= finish, "DISCOVERY.md", "query date outside run")
        except (ValueError, TypeError, UnboundLocalError):
            check(False, "DISCOVERY.md", "invalid query date")
    saturation = discovery.get("saturation", {})
    if saturation.get("saturation_reached"):
        last = queries[-3:]
        check(len(last) == 3 and len({q.get("family") for q in last}) == 3 and
              all(not q.get("new_competitor_ids") for q in last) and saturation.get("zero_new_family_streak", 0) >= 3,
              "DISCOVERY.md", "saturation lacks three independent zero-new query families")
    if package_version == "ci-package/v1.1":
        query_ids = {q.get("query_id") for q in queries if isinstance(q, dict)}
        valid_currencies = set((Path(__file__).parent.parent / "schemas/currencies.txt").read_text().split())

        def evidence_refs(refs, entity, path, label):
            check(isinstance(refs, list), path, label + " must be a list")
            for fid in refs if isinstance(refs, list) else []:
                check(isinstance(fid, str) and fid in findings and
                      (entity is None or findings[fid].get("competitor_id") == entity),
                      path, label + " has a missing or cross-entity finding")

        def check_items(items, entity, path, key_set, key_field="key"):
            check(isinstance(items, list), path, "structured observations must be a list")
            for item in items if isinstance(items, list) else []:
                if not isinstance(item, dict):
                    check(False, path, "structured observation must be an object")
                    continue
                check(item.get(key_field) in key_set, path, "unsupported normalized value: " + str(item.get(key_field)))
                evidence_refs(item.get("finding_ids"), entity, path, "finding_ids")

        for competitor in included:
            cid = competitor["id"]
            profile = records.get(f"competitors/{cid}/PROFILE.md", {})
            coverage = competitor.get("dimension_coverage")
            check(isinstance(coverage, dict) and set(coverage) == DIMENSIONS_V11, cid,
                  "v1.1 dimension_coverage must contain all 12 standard dimensions")
            check(profile.get("dimension_coverage") == coverage, cid,
                  "profile/directory dimension_coverage mismatch")
            check(profile.get("coverage_metrics") == competitor.get("coverage_metrics") and
                  profile.get("research_gaps") == competitor.get("research_gaps"), cid,
                  "profile/directory coverage metrics or research gaps mismatch")
            if not isinstance(coverage, dict):
                continue
            state_counts = {state: 0 for state in DIMENSION_STATES}
            supported_count = 0
            attempted_count = 0
            for dimension in DIMENSIONS_V11:
                item = coverage.get(dimension)
                if not isinstance(item, dict):
                    check(False, cid, "missing coverage record for " + dimension)
                    continue
                state = item.get("state")
                check(state in DIMENSION_STATES, cid, "invalid coverage state for " + dimension)
                if state not in DIMENSION_STATES:
                    continue
                state_counts[state] += 1
                source_ids = item.get("source_ids", [])
                finding_ids = item.get("finding_ids", [])
                attempted_query_ids = item.get("query_ids", [])
                evidence_refs(finding_ids, cid, f"competitors/{cid}/PROFILE.md", dimension + " finding_ids")
                check(isinstance(source_ids, list), cid, "coverage source_ids must be a list")
                for sid in source_ids if isinstance(source_ids, list) else []:
                    check(sid in sources and sources[sid].get("competitor_id") == cid, cid,
                          "coverage source reference is missing or cross-entity")
                check(isinstance(attempted_query_ids, list), cid, "coverage query_ids must be a list")
                check(all(qid in query_ids for qid in attempted_query_ids if isinstance(qid, str)), cid,
                      "coverage references an unknown query")
                reason = item.get("reason")
                check(reason is None or isinstance(reason, str), cid, "coverage reason must be text or null")
                if state in {"SUPPORTED", "PARTIAL"}:
                    check(bool(finding_ids), cid, state + " requires evidence findings for " + dimension)
                    supported_count += 1
                if state == "SUPPORTED":
                    check(bool(source_ids), cid, "SUPPORTED requires source references for " + dimension)
                if state == "PARTIAL":
                    check(bool(reason), cid, "PARTIAL requires a limitation for " + dimension)
                if state == "SEARCHED_UNKNOWN":
                    check(bool(attempted_query_ids) and not finding_ids, cid,
                          "SEARCHED_UNKNOWN requires attempted query IDs and no finding for " + dimension)
                    check(bool(reason), cid, "SEARCHED_UNKNOWN requires a search result note for " + dimension)
                if state == "NOT_RESEARCHED":
                    check(not attempted_query_ids and not finding_ids, cid,
                          "NOT_RESEARCHED cannot claim query or finding evidence for " + dimension)
                    check(bool(reason), cid, "NOT_RESEARCHED requires a documented reason for " + dimension)
                    if competitor.get("classification") == "direct":
                        check(False, cid, "direct competitor has an unattempted dimension: " + dimension, "WARNING")
                if state == "RESTRICTED":
                    check(bool(source_ids) and bool(reason), cid,
                          "RESTRICTED requires a blocked/restricted source and reason for " + dimension)
                    check(any(sid in sources and sources[sid].get("access_class") in
                              {"DIRECT_PROHIBITED", "UNKNOWN", "DISCOVERY_ONLY"} for sid in source_ids
                              if isinstance(sid, str)), cid,
                          "RESTRICTED requires a source with a limiting access class for " + dimension)
                    check(not finding_ids, cid, "RESTRICTED cannot carry positive findings for " + dimension)
                if state != "NOT_RESEARCHED":
                    attempted_count += 1
            denominator = len(DIMENSIONS_V11)
            expected_coverage = round(supported_count / denominator * 100, 2)
            expected_attempted = round(attempted_count / denominator * 100, 2)
            metrics = competitor.get("coverage_metrics")
            check(isinstance(metrics, dict), cid, "missing coverage_metrics")
            if isinstance(metrics, dict):
                check(metrics.get("coverage_counts") == state_counts, cid, "coverage_counts do not match states")
                check(metrics.get("coverage_percentage") == expected_coverage, cid,
                      "coverage_percentage must equal (SUPPORTED + PARTIAL) / 12")
                check(metrics.get("research_attempt_percentage") == expected_attempted, cid,
                      "research_attempt_percentage must equal attempted dimensions / 12")
                check(metrics.get("formula") == "(SUPPORTED + PARTIAL) / applicable_dimensions * 100",
                      cid, "coverage formula is missing or unsupported")
                check(metrics.get("limitations") and "quality" in str(metrics.get("limitations")).lower(), cid,
                      "coverage metric must state that coverage is not competitor quality")
            gaps = competitor.get("research_gaps")
            check(isinstance(gaps, list), cid, "research_gaps must be a list")
            gap_map = {}
            for gap in gaps if isinstance(gaps, list) else []:
                if not isinstance(gap, dict):
                    check(False, cid, "research gap must be an object")
                    continue
                dimension, state = gap.get("dimension"), gap.get("state")
                check(dimension in DIMENSIONS_V11 and state in DIMENSION_STATES and bool(gap.get("note")), cid,
                      "research gap requires a supported dimension, state and note")
                check(dimension not in gap_map, cid, "duplicate research gap dimension")
                gap_map[dimension] = gap
            for dimension, item in coverage.items():
                if isinstance(item, dict) and item.get("state") in {"SEARCHED_UNKNOWN", "NOT_RESEARCHED", "RESTRICTED"}:
                    check(dimension in gap_map and gap_map[dimension].get("state") == item.get("state"), cid,
                          "research gap missing or inconsistent for " + dimension)
            source_attempts = profile.get("source_attempts")
            check(isinstance(source_attempts, list), cid, "source_attempts must be a list")
            attempt_types = set()
            for attempt in source_attempts if isinstance(source_attempts, list) else []:
                if not isinstance(attempt, dict):
                    check(False, cid, "source attempt must be an object")
                    continue
                check(attempt.get("source_type") in {"official_product", "official_pricing", "official_docs",
                      "official_company", "official_press", "public_social", "retailer", "marketplace",
                      "directory", "third_party", "search_snippet"}, cid, "invalid source attempt type")
                check(attempt.get("outcome") in {"collected", "blocked", "unavailable", "not_found"}, cid,
                      "invalid source attempt outcome")
                check(bool(attempt.get("note")), cid, "source attempt needs an outcome note")
                attempt_types.add(attempt.get("source_type"))
                for sid in attempt.get("source_ids", []):
                    check(sid in sources and sources[sid].get("competitor_id") == cid, cid,
                          "source attempt has a missing or cross-entity source")
            if competitor.get("classification") == "direct":
                check(len(attempt_types) >= 2, cid,
                      "direct dossier requires a multi-source attempt across at least two source types")

            for field in ("brand_name", "short_description", "business_model", "primary_customer",
                          "primary_geography", "online_presence", "physical_presence", "sales_model",
                          "primary_offering", "sales_channels_observed", "trust_signals", "geography_details",
                          "logo_url", "favicon_url", "brand_initials", "short_description_finding_ids",
                          "profile_field_evidence", "primary_categories"):
                check(field in profile, cid, "v1.1 profile missing " + field)
            check(profile.get("brand_name") == competitor.get("brand_name"), cid,
                  "profile/directory brand_name mismatch")
            check(profile.get("short_description") == competitor.get("short_description"), cid,
                  "profile/directory short_description mismatch")
            check(profile.get("primary_categories") == competitor.get("primary_categories"), cid,
                  "profile/directory primary_categories mismatch")
            check(isinstance(profile.get("primary_categories"), list) and
                  set(profile.get("primary_categories", [])) <= EYEWEAR_PRODUCTS, cid,
                  "primary_categories contains unsupported eyewear values")
            field_evidence = profile.get("profile_field_evidence")
            check(isinstance(field_evidence, dict), cid, "profile_field_evidence must be an object")
            for field in ("brand_name", "short_description", "business_model", "primary_customer",
                          "primary_geography", "online_presence", "physical_presence", "sales_model",
                          "primary_offering"):
                value = profile.get(field)
                refs = field_evidence.get(field, []) if isinstance(field_evidence, dict) else []
                if value not in (None, "", "unknown"):
                    evidence_refs(refs, cid, f"competitors/{cid}/PROFILE.md", field + " evidence")
                    check(bool(refs), cid, field + " requires evidence when populated")
            for field in ("brand_name", "short_description", "business_model", "primary_customer",
                          "primary_geography", "online_presence", "physical_presence", "sales_model",
                          "primary_offering"):
                refs = field_evidence.get(field, []) if isinstance(field_evidence, dict) else []
                check(profile.get(field) in (None, "", "unknown") or refs == profile.get(field + "_finding_ids", refs),
                      cid, field + " evidence fields are inconsistent")
            check(profile.get("online_presence") in {"observed", "unknown"}, cid, "invalid online_presence")
            check(profile.get("physical_presence") in {"observed", "unknown"}, cid, "invalid physical_presence")
            description_refs = profile.get("short_description_finding_ids", [])
            if profile.get("short_description"):
                evidence_refs(description_refs, cid, f"competitors/{cid}/PROFILE.md", "short_description_finding_ids")
                check(bool(description_refs), cid, "short_description requires evidence")
                check(len(str(profile["short_description"]).split(".")) <= 4, cid,
                      "short_description must be limited to 1-3 factual sentences")
            for asset_key in ("logo_url", "favicon_url"):
                value = profile.get(asset_key)
                if value is not None and not public_url(value):
                    check(False, cid, "invalid optional brand asset URL: " + asset_key, "WARNING")
            initials = profile.get("brand_initials")
            check(initials is None or (isinstance(initials, str) and 1 <= len(initials) <= 4), cid,
                  "brand_initials must contain 1-4 characters")
            check(initials is None or profile.get("brand_initials_formula") ==
                  "first character of each brand-name word, truncated to four characters", cid,
                  "brand_initials requires a documented derivation formula")
            if profile.get("physical_presence") == "observed":
                check(any(isinstance(place, dict) and place.get("level") in {"city", "region", "national"}
                          for place in profile.get("geography_details", [])), cid,
                      "observed physical presence requires a sourced physical geography")
            geography_details = profile.get("geography_details")
            check(isinstance(geography_details, list), cid, "geography_details must be a list")
            for place in geography_details if isinstance(geography_details, list) else []:
                if not isinstance(place, dict):
                    check(False, cid, "geography detail must be an object")
                    continue
                check(place.get("level") in {"city", "region", "national", "online_only", "physical_only", "omnichannel"},
                      cid, "invalid geography level")
                evidence_refs(place.get("finding_ids"), cid, f"competitors/{cid}/PROFILE.md", "geography finding_ids")
            channels = profile.get("sales_channels_observed")
            check_items(channels, cid, f"competitors/{cid}/PROFILE.md", SALES_CHANNELS)
            check_items(profile.get("trust_signals"), cid, f"competitors/{cid}/PROFILE.md", TRUST_SIGNALS)

            offerings = records.get(f"competitors/{cid}/OFFERINGS.md", {})
            check_items(offerings.get("product_categories"), cid, f"competitors/{cid}/OFFERINGS.md", EYEWEAR_PRODUCTS)
            check_items(offerings.get("services"), cid, f"competitors/{cid}/OFFERINGS.md", EYEWEAR_SERVICES)
            pricing = records.get(f"competitors/{cid}/PRICING.md", {})
            observations = pricing.get("price_observations")
            check(isinstance(observations, list), cid, "price_observations must be a list")
            grouped_prices = {}
            for observation in observations if isinstance(observations, list) else []:
                if not isinstance(observation, dict):
                    check(False, cid, "price observation must be an object")
                    continue
                amount, currency, unit = observation.get("amount"), observation.get("currency"), observation.get("unit")
                check(currency in valid_currencies, cid, "price record has invalid currency")
                check(observation.get("price_type") in {"visible_price", "list_price", "sale_price", "service_fee",
                      "shipping_threshold", "installment"}, cid, "unsupported price_type")
                check(observation.get("promotion_state") in {"current", "historical", "unknown"}, cid,
                      "invalid price promotion_state")
                ranged = "amount_min" in observation or "amount_max" in observation
                if ranged:
                    lower, upper = observation.get("amount_min"), observation.get("amount_max")
                    valid_bounds = all(isinstance(value, (int, float)) and not isinstance(value, bool)
                                       and math.isfinite(value) and value >= 0 for value in (lower, upper))
                    check(valid_bounds and lower <= upper if valid_bounds else False, cid,
                          "price range requires ordered non-negative amount_min and amount_max")
                    refs = observation.get("finding_ids")
                    check(isinstance(refs, list) and len(refs) == 2 and len(set(refs)) == 2, cid,
                          "price range requires separate minimum and maximum finding IDs")
                    linked = [findings.get(fid) for fid in refs] if isinstance(refs, list) else []
                    check(all(f is not None and f.get("competitor_id") == cid for f in linked), cid,
                          "price range requires linked findings for both endpoints")
                    if len(linked) == 2 and all(linked):
                        values = [f.get("normalized_value", f.get("observed_value")) for f in linked]
                        check(all(f.get("value_type") == "money" and f.get("currency") == currency
                                  and f.get("unit") == unit for f in linked) and
                              set(values) == {lower, upper}, cid,
                              "price range findings contradict its bounds, currency or unit")
                        check(set(observation.get("source_ids", [])) <=
                              set(s for f in linked for s in f.get("source_ids", [])), cid,
                              "price range sources must be supported by its findings")
                    prices = (lower, upper) if valid_bounds else (None, None)
                    fids = refs if isinstance(refs, list) else []
                else:
                    numeric = isinstance(amount, (int, float)) and not isinstance(amount, bool) and math.isfinite(amount)
                    check(numeric and amount >= 0, cid, "price amount must be a non-negative number")
                    fid = observation.get("finding_id")
                    check(fid in findings and findings[fid].get("competitor_id") == cid, cid,
                          "price observation requires a linked finding")
                    if fid in findings:
                        finding = findings[fid]
                        check(finding.get("value_type") == "money" and finding.get("currency") == currency and
                              finding.get("normalized_value", finding.get("observed_value")) == amount and
                              (unit is None or finding.get("unit") == unit), cid,
                              "price record contradicts its finding or changes the source currency")
                        check(set(observation.get("source_ids", [])) <= set(finding.get("source_ids", [])), cid,
                              "price source IDs must be supported by its finding")
                    prices = (amount, amount) if numeric else (None, None)
                    fids = [fid] if isinstance(fid, str) else []
                try:
                    observed_at = timestamp(observation.get("observed_at"))
                    check(start <= observed_at <= finish, cid, "price observation date outside run")
                except (TypeError, ValueError):
                    check(False, cid, "invalid price observation date")
                if prices[0] is not None and currency in valid_currencies:
                    grouped_prices.setdefault((observation.get("category"), currency, unit), []).append(
                        (prices[0], prices[1], (prices[0] + prices[1]) / 2, fids, ranged))
            summaries = pricing.get("price_summaries")
            check(isinstance(summaries, list), cid, "price_summaries must be a list")
            summary_keys = set()
            for summary in summaries if isinstance(summaries, list) else []:
                if not isinstance(summary, dict):
                    check(False, cid, "price summary must be an object")
                    continue
                key = (summary.get("category"), summary.get("currency"), summary.get("unit"))
                data = grouped_prices.get(key, [])
                check(len(data) >= 2, cid, "price summary requires at least two comparable observations")
                range_formula = ("minimum = min(lower bounds); maximum = max(upper bounds); median = median of "
                                 "each observation midpoint; count = price observations, grouped by category, currency and unit")
                legacy_formula = "min, max, median, count over observed prices grouped by category and currency"
                expected_formula = range_formula if any(item[4] for item in data) or key[2] is not None else legacy_formula
                check(summary.get("formula") == expected_formula, cid,
                      "price summary formula is missing or unsupported")
                if data:
                    lower_bounds = [x[0] for x in data]
                    upper_bounds = [x[1] for x in data]
                    midpoints = [x[2] for x in data]
                    input_findings = {fid for item in data for fid in item[3]}
                    check(summary.get("minimum_observed_price") == min(lower_bounds) and
                          summary.get("maximum_observed_price") == max(upper_bounds) and
                          summary.get("median_observed_price") == statistics.median(midpoints) and
                          summary.get("price_observation_count") == len(data), cid,
                          "price summary does not match source observations")
                    check(set(summary.get("finding_ids", [])) == input_findings, cid,
                          "price summary finding inputs do not match observations")
                check(summary.get("limitations") and "market" in str(summary.get("limitations")).lower(), cid,
                      "price summary must state it is not a market price estimate")
                check(key not in summary_keys, cid, "duplicate price summary group")
                summary_keys.add(key)
            for key, data in grouped_prices.items():
                if len(data) >= 2:
                    check(key in summary_keys, cid, "missing derivation for a comparable price group")
            for promotion in pricing.get("promotions", []):
                if not isinstance(promotion, dict):
                    check(False, cid, "promotion must be an object")
                    continue
                check(promotion.get("type") in PROMOTION_TYPES and promotion.get("state") in
                      {"current", "historical", "unknown"}, cid, "invalid promotion observation")
                evidence_refs(promotion.get("finding_ids"), cid, f"competitors/{cid}/PRICING.md", "promotion finding_ids")

            positioning = records.get(f"competitors/{cid}/POSITIONING.md", {})
            check_items(positioning.get("themes"), cid, f"competitors/{cid}/POSITIONING.md", POSITIONING_THEMES)
            experience = records.get(f"competitors/{cid}/EXPERIENCE.md", {})
            check_items(experience.get("capabilities"), cid, f"competitors/{cid}/EXPERIENCE.md", EXPERIENCE_CAPABILITIES)
            digital = records.get(f"competitors/{cid}/DIGITAL.md", {})
            check_items(digital.get("capabilities"), cid, f"competitors/{cid}/DIGITAL.md", DIGITAL_CAPABILITIES)

        dimension_counts = {dimension: {state: 0 for state in DIMENSION_STATES}
                            for dimension in DIMENSIONS_V11}
        for competitor in included:
            for dimension, item in competitor.get("dimension_coverage", {}).items():
                if isinstance(item, dict) and item.get("state") in DIMENSION_STATES:
                    dimension_counts[dimension][item["state"]] += 1
        coverage_report = records.get("DISCOVERY.md", {}).get("coverage", {})
        check(coverage_report.get("competitor_dimension_counts") == dimension_counts,
              "DISCOVERY.md", "aggregate dimension counts do not match competitor dossiers")
        check(coverage_report.get("coverage_formula") ==
              "per competitor: (SUPPORTED + PARTIAL) / 12 applicable dimensions * 100",
              "DISCOVERY.md", "coverage formula is missing or unsupported")

        for rel, document in records.items():
            if rel.startswith("analysis/"):
                for hypothesis in document.get("hypotheses", []):
                    if not isinstance(hypothesis, dict):
                        check(False, rel, "hypothesis must be an object")
                        continue
                    check(hypothesis.get("type") in {"opportunity", "risk"} and bool(hypothesis.get("id")) and
                          bool(hypothesis.get("title")) and bool(hypothesis.get("summary")) and
                          bool(hypothesis.get("limitations")) and
                          hypothesis.get("evidence_strength") in {"strong", "medium", "weak"},
                          rel, "hypothesis needs type, identity, evidence strength and limitations")
                    refs = hypothesis.get("related_finding_ids", hypothesis.get("finding_ids", []))
                    evidence_refs(refs, None, rel, "hypothesis finding_ids")
                    related = hypothesis.get("related_competitor_ids", [])
                    check(isinstance(related, list) and bool(related), rel,
                          "hypothesis must identify related competitors")
                    for related_id in related if isinstance(related, list) else []:
                        check(related_id in {c.get("id") for c in included}, rel,
                              "hypothesis references an unknown competitor")
                    check(bool(refs), rel, "opportunity/risk hypothesis requires evidence")
    for key, count in (("file_count", len(records)), ("competitor_count", len(included)),
                       ("direct_competitor_count", sum(c.get("classification") == "direct" for c in included)),
                       ("source_count", len(sources)), ("finding_count", len(findings))):
        check(type(manifest.get(key)) is int and manifest.get(key) == count, "MANIFEST.md", key + " mismatch")
    check(bool(findings), "MANIFEST.md", "no evidence-supported findings", "WARNING")
    if check_hashes and not any(i["status"] == "FAIL" for i in issues):
        expected_result = "WARNING" if issues else "PASS"
        check(report.get("result") == expected_result, "VALIDATION.md", "validation report is stale")
    return issues, records


def validate(root: Path, check_hashes=True):
    try:
        return _validate(root, check_hashes)
    except Exception as exc:
        return [{"status": "FAIL", "path": str(root), "message": "malformed package: " + str(exc)}], {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_dir", type=Path)
    args = parser.parse_args()
    try:
        issues, _ = validate(args.package_dir)
    except Exception as exc:
        issues = [{"status": "FAIL", "path": str(args.package_dir), "message": "malformed package: " + str(exc)}]
    for issue in issues:
        print(f"{issue['status']}: {issue['path']}: {issue['message']}")
    failed = any(i["status"] == "FAIL" for i in issues)
    print("FAIL" if failed else "WARNING" if issues else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
