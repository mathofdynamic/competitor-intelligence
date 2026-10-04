"""Compare validated snapshots by stable identity/field/context; never infer inactivity."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from package_io import read_document, write_document
from validate_package import validate


def compare(previous: Path, current: Path):
    old_issues, old = validate(previous)
    new_issues, new = validate(current)
    if any(i["status"] == "FAIL" for i in old_issues + new_issues):
        raise ValueError("both packages must validate before comparison")
    if old["MANIFEST.md"]["company_id"] != new["MANIFEST.md"]["company_id"]:
        raise ValueError("focal company mismatch")
    if old["MANIFEST.md"]["package_id"] == new["MANIFEST.md"]["package_id"]:
        raise ValueError("previous and current package IDs must differ")

    def grouped(records):
        groups = {}
        for d in records.values():
            if d["document_type"] == "finding":
                dimension = {"experience": "customer_experience", "channels": "sales_channels",
                             "digital": "digital_presence"}.get(d["dimension"], d["dimension"])
                key = (d["competitor_id"], dimension, d["field_key"],
                       json.dumps(d.get("context", {}), sort_keys=True, ensure_ascii=False))
                groups.setdefault(key, []).append(d)
        return groups

    before, after = grouped(old), grouped(new)
    changes = []
    for key in sorted(set(before) | set(after)):
        a, b = before.get(key, []), after.get(key, [])

        def values(records):
            return sorted(({"value": f.get("normalized_value", f["observed_value"]),
                            "currency": f.get("currency"), "unit": f.get("unit")}
                           for f in records), key=lambda v: json.dumps(v, sort_keys=True))

        if values(a) == values(b):
            continue
        entity, dimension, field, _ = key
        kind = {"pricing": "pricing", "offering": "offering", "positioning": "positioning",
                "experience": "service_policy", "channels": "channel_feature", "digital": "channel_feature"}.get(dimension, "not_observed")
        if not a and b and new["MANIFEST.md"].get("schema_version") == "ci-package/v1.1":
            kind = "newly_observed"
        elif not b:
            kind = "not_observed"
        if a and b and new["MANIFEST.md"].get("schema_version") == "ci-package/v1.1":
            old_coverage = old["COMPETITORS.md"].get("competitors", [])
            new_coverage = new["COMPETITORS.md"].get("competitors", [])
            old_entry = next((c for c in old_coverage if c.get("id") == entity), None)
            new_entry = next((c for c in new_coverage if c.get("id") == entity), None)
            if old_entry and new_entry:
                old_state = old_entry.get("dimension_coverage", {}).get(dimension, {}).get("state")
                new_state = new_entry.get("dimension_coverage", {}).get(dimension, {}).get("state")
                if old_state in {"SEARCHED_UNKNOWN", "NOT_RESEARCHED", "RESTRICTED"} and new_state in {"SUPPORTED", "PARTIAL"}:
                    kind = "newly_observed"
        changes.append({"change_id": f"change-{len(changes) + 1:04d}", "entity_id": entity,
                        "dimension": dimension, "field_key": field, "change_type": kind,
                        "previous_value": values(a), "current_value": values(b),
                        "previous_finding_ids": [f["finding_id"] for f in a],
                        "current_finding_ids": [f["finding_id"] for f in b],
                        "interpretation": "Observed snapshot difference; requires analyst reconciliation.",
                        "limitations": ["Matched by stable ID, field and exact context; sampling changes can explain differences."]})
    old_ids = {c["id"] for c in old["COMPETITORS.md"]["competitors"]}
    for c in new["COMPETITORS.md"]["competitors"]:
        if c["id"] not in old_ids:
            changes.append({"change_id": f"change-{len(changes) + 1:04d}", "entity_id": c["id"],
                            "dimension": "identity", "field_key": "competitor", "change_type": "new_competitor",
                            "previous_value": None, "current_value": c["name"], "previous_finding_ids": [],
                            "current_finding_ids": [], "interpretation": "Newly included in this scoped snapshot.",
                            "limitations": ["Not evidence the company itself is new."]})
    data = {k: new["MANIFEST.md"][k] for k in ("schema_version", "package_id", "run_id")}
    data.update(document_type="changelog", generated_at=datetime.now(timezone.utc).isoformat(),
                previous_package_id=old["MANIFEST.md"]["package_id"], changes=changes,
                limitations=["Draft comparison: main agent must reconcile identities, scope, conflicts and normalization."])
    return data


def stable_identity_matches(previous_records, current_records):
    """Preserve IDs only for exact stable-ID/name/domain matches; review ambiguous cases manually."""
    old = {c["id"]: c for c in previous_records["COMPETITORS.md"].get("competitors", [])}
    new = {c["id"]: c for c in current_records["COMPETITORS.md"].get("competitors", [])}
    matches = []
    for cid in sorted(old.keys() & new.keys()):
        before, after = old[cid], new[cid]
        same_name = str(before.get("name", "")).strip().casefold() == str(after.get("name", "")).strip().casefold()
        same_domain = str(before.get("domain", "")).strip().lower() == str(after.get("domain", "")).strip().lower()
        if same_name or same_domain:
            matches.append({"previous_id": cid, "current_id": cid,
                            "match_basis": "stable ID with matching normalized name or domain; aliases still require review",
                            "confidence": "medium" if same_name and same_domain else "weak"})
    return matches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("previous", type=Path)
    parser.add_argument("current", type=Path)
    args = parser.parse_args()
    try:
        data = compare(args.previous, args.current)
        matches = []
        if data.get("schema_version") == "ci-package/v1.1":
            _, old_records = validate(args.previous)
            _, current_records = validate(args.current)
            matches = stable_identity_matches(old_records, current_records)
        write_document(args.current / "analysis/CHANGELOG.md", data,
                       "# Changes\n\nSnapshot differences require main-agent review. Missing observations do not prove inactivity.\n")
        run, body = read_document(args.current / "RUN.md")
        run["previous_package_id"] = data["previous_package_id"]
        if data.get("schema_version") == "ci-package/v1.1":
            run["previous_competitor_matches"] = matches
        write_document(args.current / "RUN.md", run, body)
        print("Changelog written. Review, then seal and validate the current package again.")
    except Exception as exc:
        print("FAIL: " + str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
