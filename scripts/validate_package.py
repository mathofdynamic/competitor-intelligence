"""Validate CI Package v1 offline. Exit 1 on FAIL; never approve evidence."""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import math
import re
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
            check(d.get("schema_version") == "ci-package/v1", rel, "unsupported schema version")
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
                      "evidence_coverage", "last_observed_at"):
            check(field in c, cid, "missing " + field)
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
                "unknowns", "profile_provenance", "finding_ids"):
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
                          "collection_method", "robots_status", "terms_status", "content_sha256", "status", "evidence_text"):
                check(field in d, rel, "missing " + field)
            for field in ("url", "canonical_url"):
                check(public_url(d.get(field)), rel, "invalid public " + field)
            check(d.get("source_type") in {"official_product", "official_pricing", "official_docs", "official_company",
                  "official_press", "public_social", "retailer", "marketplace", "directory", "third_party", "search_snippet"}, rel, "invalid source_type")
            check(d.get("collection_method") in {"browser_public", "http_public", "manual_review", "public_search"}, rel, "invalid collection method")
            check(d.get("robots_status") in {"allowed", "disallowed", "unknown"}, rel, "invalid robots_status")
            check(d.get("terms_status") in {"reviewed_allowed", "reviewed_restricted", "unknown"}, rel, "invalid terms_status")
            check(d.get("status") in {"collected", "blocked", "unverified", "stale"}, rel, "invalid source status")
            check(d.get("status") != "collected" or (d.get("robots_status") == "allowed" and
                  d.get("terms_status") == "reviewed_allowed"), rel, "collection permission unsupported")
            evidence = d.get("evidence_text")
            check(isinstance(evidence, str) and len(evidence) <= 4000, rel, "bounded evidence_text required")
            if isinstance(evidence, str):
                check(d.get("content_sha256") == hashlib.sha256(evidence.encode("utf-8")).hexdigest(), rel, "content hash mismatch")
            try:
                accessed = timestamp(d.get("accessed_at"))
                check(start <= accessed <= finish, rel, "source date outside run")
            except (ValueError, TypeError, UnboundLocalError):
                check(False, rel, "invalid source date")
        else:
            for field in ("dimension", "field_key", "observed_value", "value_type", "observed_at", "source_ids", "evidence_strength", "review_status", "notes"):
                check(field in d, rel, "missing " + field)
            check(d.get("review_status") == "needs_review", rel, "agent findings must need review")
            check(d.get("dimension") in DIMENSIONS or d.get("dimension") in records.get("RUN.md", {}).get("extension_dimensions", []), rel, "unsupported dimension")
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
                check(s.get("status") == "collected" and s.get("source_type") != "search_snippet"
                      and bool(s.get("evidence_text")), fid, "source cannot support a factual finding")
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
            check(cell.get("dimension") in DIMENSIONS or cell.get("dimension") in records.get("RUN.md", {}).get("extension_dimensions", []), rel, "cell has unsupported dimension")
            refs = cell.get("finding_ids", [])
            for fid in refs if isinstance(refs, list) else []:
                check(isinstance(fid, str) and fid in findings and findings[fid].get("competitor_id") == cell.get("entity_id"), rel, "cell has broken/cross-entity evidence")
                if isinstance(fid, str) and fid in findings:
                    linked = findings[fid]
                    check(linked.get("dimension") == cell.get("dimension") and linked.get("field_key") == cell.get("field_key"), rel, "cell evidence belongs to another field")
                    check(not linked.get("conflict_group_id") or cell.get("status") == "conflict", rel, "conflicting finding cannot become a resolved chart value")
            state = cell.get("status")
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
