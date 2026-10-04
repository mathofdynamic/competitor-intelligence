"""Offline contract, negative validation, integrity and packaging regressions."""
import copy
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from package_factory import make_package, TIME
from build_package import build, seal
from compare_packages import compare, stable_identity_matches
from package_io import read_document, write_document
from validate_package import validate
from validate_package import DIMENSIONS_V11


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = make_package(self.base / "competitor-intelligence-package")

    def edit(self, rel, **updates):
        data, body = read_document(self.root / rel)
        data.update(updates)
        write_document(self.root / rel, data, body)

    def assert_fail(self, text):
        issues, _ = validate(self.root)
        self.assertTrue(any(i["status"] == "FAIL" and text in i["message"] for i in issues), issues)
        with self.assertRaises(ValueError):
            build(self.root)

    def make_v11(self, previous_package_id=None):
        return make_package(self.base / "ci-package-v1.1", "deep-fixture", schema_version="ci-package/v1.1",
                            previous_package_id=previous_package_id)

    def test_valid_package_and_manifest_only_zip(self):
        self.assertEqual(validate(self.root)[0], [])
        artifact = build(self.root)
        manifest, _ = read_document(self.root / "MANIFEST.md")
        with zipfile.ZipFile(artifact) as z:
            self.assertEqual(set(z.namelist()), {"competitor-intelligence-package/" + e["path"] for e in manifest["files"]})
            self.assertIsNone(z.testzip())
        with self.assertRaises(ValueError):
            build(self.root)

    def test_v11_deep_dossier_and_v1_compatibility(self):
        self.assertEqual(validate(self.root)[0], [])
        deep = self.make_v11()
        issues, records = validate(deep)
        self.assertFalse(any(i["status"] == "FAIL" for i in issues), issues)
        self.assertEqual(records["MANIFEST.md"]["schema_version"], "ci-package/v1.1")
        competitor = records["COMPETITORS.md"]["competitors"][0]
        self.assertEqual(set(competitor["dimension_coverage"]), DIMENSIONS_V11)
        self.assertEqual(competitor["coverage_metrics"]["coverage_percentage"], 75.0)
        self.assertGreaterEqual(records["MANIFEST.md"]["source_count"], 10)
        self.assertGreaterEqual(records["MANIFEST.md"]["finding_count"], 10)
        self.assertTrue(any(i["status"] == "WARNING" and "unattempted dimension" in i["message"]
                            for i in issues), issues)
        self.assertTrue(build(deep).exists())

    def test_v11_coverage_states_and_reason_are_enforced(self):
        self.root = self.make_v11()
        directory, _ = read_document(self.root / "COMPETITORS.md")
        directory["competitors"][0]["dimension_coverage"]["physical_presence"]["reason"] = None
        self.edit("COMPETITORS.md", competitors=directory["competitors"])
        self.assert_fail("NOT_RESEARCHED requires a documented reason")

    def test_v11_direct_competitor_must_try_multiple_source_types(self):
        self.root = self.make_v11()
        profile, _ = read_document(self.root / "competitors/sample-optics/PROFILE.md")
        profile["source_attempts"] = [profile["source_attempts"][0]]
        self.edit("competitors/sample-optics/PROFILE.md", source_attempts=profile["source_attempts"])
        self.assert_fail("multi-source attempt")

    def test_v11_searched_unknown_requires_targeted_query_ids(self):
        self.root = self.make_v11()
        directory, _ = read_document(self.root / "COMPETITORS.md")
        directory["competitors"][0]["dimension_coverage"]["customer_experience"]["query_ids"] = []
        self.edit("COMPETITORS.md", competitors=directory["competitors"])
        self.assert_fail("SEARCHED_UNKNOWN requires attempted query IDs")

    def test_v11_restricted_state_requires_access_record(self):
        self.root = self.make_v11()
        directory, _ = read_document(self.root / "COMPETITORS.md")
        directory["competitors"][0]["dimension_coverage"]["trust"]["source_ids"] = []
        self.edit("COMPETITORS.md", competitors=directory["competitors"])
        self.assert_fail("RESTRICTED requires a blocked/restricted source and reason")

    def test_v11_price_summaries_preserve_currency_and_inputs(self):
        self.root = self.make_v11()
        pricing, _ = read_document(self.root / "competitors/sample-optics/PRICING.md")
        pricing["price_observations"][0]["currency"] = "USD"
        self.edit("competitors/sample-optics/PRICING.md", price_observations=pricing["price_observations"])
        self.assert_fail("price record contradicts its finding or changes the source currency")

    def test_v11_price_range_preserves_displayed_unit_and_atomic_endpoints(self):
        self.root = self.make_v11()
        for rel, value, bound in (("findings/finding-price.md", 2000000, "minimum"),
                                  ("findings/finding-price-two.md", 3000000, "maximum")):
            finding, body = read_document(self.root / rel)
            finding.update(field_key="visible_price_" + bound,
                           observed_value=f"{value} toman", normalized_value=value,
                           currency="IRR", unit="toman", value_type="money")
            write_document(self.root / rel, finding, body)
        for source_id, amount in (("source-price", 2000000), ("source-price-two", 3000000)):
            rel = f"sources/{source_id}.md"
            source, body = read_document(self.root / rel)
            source["evidence_text"] = f"Synthetic range endpoint: {amount} toman."
            source["content_sha256"] = hashlib.sha256(source["evidence_text"].encode("utf-8")).hexdigest()
            write_document(self.root / rel, source, body)
        pricing, body = read_document(self.root / "competitors/sample-optics/PRICING.md")
        pricing["price_observations"] = [{
            "category": "optical_frames", "item_or_service": "sample frame with variants",
            "amount_min": 2000000, "amount_max": 3000000, "currency": "IRR", "unit": "toman",
            "price_type": "visible_price", "promotion_state": "unknown", "observed_at": TIME,
            "source_ids": ["source-price", "source-price-two"],
            "finding_ids": ["finding-price", "finding-price-two"]}]
        pricing["price_summaries"] = []
        pricing["rows"] = []
        write_document(self.root / "competitors/sample-optics/PRICING.md", pricing, body)
        for rel in ("analysis/COMPARISON.md", "analysis/PRICING-ANALYSIS.md"):
            data, body = read_document(self.root / rel)
            data["rows"] = []
            write_document(self.root / rel, data, body)
        issues = seal(self.root)
        self.assertFalse(any(i["status"] == "FAIL" for i in issues), issues)

    def test_v11_price_range_rejects_reversed_or_unlinked_bounds(self):
        self.root = self.make_v11()
        for rel, value, bound in (("findings/finding-price.md", 3000000, "minimum"),
                                  ("findings/finding-price-two.md", 2000000, "maximum")):
            finding, body = read_document(self.root / rel)
            finding.update(field_key="visible_price_" + bound, observed_value=f"{value} toman",
                           normalized_value=value, currency="IRR", unit="toman", value_type="money")
            write_document(self.root / rel, finding, body)
        pricing, body = read_document(self.root / "competitors/sample-optics/PRICING.md")
        pricing["price_observations"] = [{
            "category": "optical_frames", "item_or_service": "sample frame with variants",
            "amount_min": 3000000, "amount_max": 2000000, "currency": "IRR", "unit": "toman",
            "price_type": "visible_price", "promotion_state": "unknown", "observed_at": TIME,
            "source_ids": ["source-price", "source-price-two"], "finding_ids": ["finding-price"]}]
        self.edit("competitors/sample-optics/PRICING.md", price_observations=pricing["price_observations"],
                  price_summaries=[])
        issues, _ = validate(self.root)
        self.assertTrue(any(i["status"] == "FAIL" and "ordered non-negative amount_min" in i["message"]
                            for i in issues), issues)

    def test_v11_invalid_logo_is_non_blocking_warning(self):
        self.root = self.make_v11()
        self.edit("competitors/sample-optics/PROFILE.md", logo_url="javascript:alert(1)")
        issues = seal(self.root)
        self.assertTrue(any(i["status"] == "WARNING" and "optional brand asset URL" in i["message"]
                            for i in issues), issues)
        self.assertFalse(any(i["status"] == "FAIL" for i in issues), issues)
        self.assertTrue(build(self.root).exists())

    def test_v11_taxonomies_and_opportunity_evidence_are_checked(self):
        self.root = self.make_v11()
        offering, _ = read_document(self.root / "competitors/sample-optics/OFFERINGS.md")
        offering["product_categories"][0]["key"] = "misc_optics"
        self.edit("competitors/sample-optics/OFFERINGS.md", product_categories=offering["product_categories"])
        self.assert_fail("unsupported normalized value")

        self.root = self.make_v11()
        analysis, _ = read_document(self.root / "analysis/OPPORTUNITIES.md")
        analysis["hypotheses"][0]["related_finding_ids"] = []
        analysis["hypotheses"][0]["finding_ids"] = []
        self.edit("analysis/OPPORTUNITIES.md", hypotheses=analysis["hypotheses"])
        self.assert_fail("opportunity/risk hypothesis requires evidence")

    def test_v11_previous_matching_and_changelog(self):
        previous = make_package(self.base / "previous-v1", "prior-fixture-package")
        deep = self.make_v11(previous_package_id="prior-fixture-package")
        issues, records = validate(deep)
        self.assertFalse(any(i["status"] == "FAIL" for i in issues), issues)
        self.assertEqual(records["RUN.md"]["previous_competitor_matches"][0]["previous_id"], "sample-optics")
        self.assertEqual(records["RUN.md"]["previous_competitor_matches"][0]["current_id"], "sample-optics")
        self.assertEqual(records["analysis/CHANGELOG.md"]["previous_package_id"], "prior-fixture-package")
        old_records, current_records = validate(previous)[1], records
        self.assertEqual(stable_identity_matches(old_records, current_records)[0]["current_id"], "sample-optics")
        comparison = compare(previous, deep)
        self.assertTrue(any(change["change_type"] == "newly_observed" and
                            change["dimension"] == "description" for change in comparison["changes"]))

    def test_not_researched_analysis_cell_is_distinct_from_unknown(self):
        data, body = read_document(self.root / "analysis/COMPARISON.md")
        manifest, _ = read_document(self.root / "MANIFEST.md")
        data["rows"].append({"entity_id": manifest["company_id"], "dimension": "pricing", "field_key": "visible_price",
                             "value": None, "unit": None, "currency": None, "status": "not_researched",
                             "finding_ids": [], "context": "No focal-company baseline was collected."})
        write_document(self.root / "analysis/COMPARISON.md", data, body)
        self.assertEqual(seal(self.root), [])
        self.assertEqual(validate(self.root)[0], [])

    def test_missing_source(self):
        (self.root / "sources/source-price.md").unlink()
        self.assert_fail("broken source reference")

    def test_invalid_finding_type(self):
        self.edit("findings/finding-price.md", value_type="score")
        self.assert_fail("unsupported value_type")

    def test_approval_bypass(self):
        self.edit("findings/finding-price.md", review_status="approved")
        self.assert_fail("must need review")

    def test_empty_evidence(self):
        self.edit("findings/finding-price.md", source_ids=[])
        self.assert_fail("requires source IDs")

    def test_duplicate_id(self):
        data, body = read_document(self.root / "findings/finding-price.md")
        write_document(self.root / "findings/duplicate.md", data, body)
        self.assert_fail("duplicate finding_id")

    def test_bad_url(self):
        self.edit("sources/source-price.md", url="javascript:alert(1)")
        self.assert_fail("invalid public url")

    def test_private_url(self):
        self.edit("sources/source-price.md", url="http://127.0.0.1/private")
        self.assert_fail("invalid public url")

    def test_broken_hash(self):
        with (self.root / "analysis/COMPARISON.md").open("a") as f:
            f.write("Altered body\n")
        self.assert_fail("hash mismatch")

    def test_source_content_hash(self):
        self.edit("sources/source-price.md", evidence_text="Changed excerpt")
        self.assert_fail("content hash mismatch")

    def test_commercial_reuse_restriction_does_not_block_fact_observation(self):
        self.edit("sources/source-price.md", terms_status="reviewed_restricted",
                  restriction_scope="commercial_reuse", access_reason="Factual observation is permitted; commercial copying is restricted.",
                  reuse_mode="paraphrase_only")
        issues = seal(self.root)
        self.assertFalse(any(issue["status"] == "FAIL" for issue in issues), issues)
        self.assertTrue(build(self.root).exists())

    def test_unknown_terms_do_not_block_open_public_factual_observation(self):
        self.edit("sources/source-price.md", terms_status="unknown", restriction_scope="unknown",
                  reuse_mode="paraphrase_only",
                  access_reason="Public page and robots path were accessible; terms were not located. Only normalized facts and an original paraphrase are retained.")
        issues = seal(self.root)
        self.assertFalse(any(issue["status"] == "FAIL" for issue in issues), issues)
        self.assertTrue(build(self.root).exists())

    def test_explicit_direct_access_restriction_blocks_collection(self):
        self.edit("sources/source-price.md", terms_status="reviewed_restricted",
                  restriction_scope="direct_access")
        self.assert_fail("DIRECT_ALLOWED requires public access")

    def test_discovery_only_source_is_metadata_only(self):
        source, body = read_document(self.root / "sources/source-price.md")
        source.update(source_id="source-discovery", url="https://sample.example.com/", canonical_url="https://sample.example.com/",
                      source_type="search_snippet", access_class="DISCOVERY_ONLY", access_reason="Search result used only to confirm a candidate URL.",
                      restriction_scope="unknown", reuse_mode="metadata_only", robots_status="unknown", terms_status="unknown",
                      evidence_text="", content_sha256=hashlib.sha256(b"").hexdigest())
        write_document(self.root / "sources/source-discovery.md", source, body)
        entry, entry_body = read_document(self.root / "COMPETITORS.md")
        entry["competitors"][0]["identity_source_ids"].append("source-discovery")
        write_document(self.root / "COMPETITORS.md", entry, entry_body)
        issues = seal(self.root)
        self.assertFalse(any(issue["status"] == "FAIL" for issue in issues), issues)
        self.assertTrue(build(self.root).exists())

    def test_discovery_only_source_cannot_support_a_finding(self):
        self.edit("sources/source-price.md", source_type="search_snippet", access_class="DISCOVERY_ONLY",
                  access_reason="Search result metadata only.", restriction_scope="unknown", reuse_mode="metadata_only",
                  robots_status="unknown", terms_status="unknown", evidence_text="", content_sha256=hashlib.sha256(b"").hexdigest())
        self.assert_fail("source cannot support a factual finding")

    def test_direct_prohibited_record_has_no_source_content(self):
        source, body = read_document(self.root / "sources/source-price.md")
        source.update(source_id="source-prohibited", url="https://sample.example.com/terms", canonical_url="https://sample.example.com/terms",
                      access_class="DIRECT_PROHIBITED", access_reason="An explicit source rule prohibits the intended direct research access.",
                      restriction_scope="direct_access", reuse_mode="metadata_only", robots_status="disallowed",
                      terms_status="reviewed_restricted", status="blocked", evidence_text="",
                      content_sha256=hashlib.sha256(b"").hexdigest(), policy_url="https://sample.example.com/terms")
        write_document(self.root / "sources/source-prohibited.md", source, body)
        issues = seal(self.root)
        self.assertFalse(any(issue["status"] == "FAIL" for issue in issues), issues)

    def test_malicious_path(self):
        data, body = read_document(self.root / "MANIFEST.md")
        data["files"][0]["path"] = "../secret.md"
        write_document(self.root / "MANIFEST.md", data, body)
        self.assert_fail("unsafe manifest path")

    def test_absolute_and_windows_paths(self):
        for path in ("C:/secret.md", "/etc/passwd", "sources\\secret.md", "sources/CON.md"):
            with self.subTest(path=path):
                data, body = read_document(self.root / "MANIFEST.md")
                data["files"][0]["path"] = path
                write_document(self.root / "MANIFEST.md", data, body)
                self.assert_fail("unsafe manifest path")

    def test_unsupported_schema(self):
        self.edit("findings/finding-price.md", schema_version="ci-package/v99")
        self.assert_fail("unsupported schema version")

    def test_bad_currency(self):
        self.edit("findings/finding-price.md", currency="XYZ")
        self.assert_fail("invalid ISO-4217 currency")

    def test_source_date(self):
        self.edit("sources/source-price.md", accessed_at="2099-01-01T00:00:00Z")
        self.assert_fail("source date outside run")

    def test_counts(self):
        self.edit("MANIFEST.md", finding_count=99)
        self.assert_fail("finding_count mismatch")

    def test_missing_dossier(self):
        (self.root / "competitors/sample-optics/PRICING.md").unlink()
        self.assert_fail("missing/mismatched dossier")

    def test_work_directory_and_unlisted_files(self):
        (self.root / "_work").mkdir()
        (self.root / "_work/secret.txt").write_text("must never enter ZIP")
        self.assert_fail("outside contract")

    def test_unknown_cannot_be_zero(self):
        data, _ = read_document(self.root / "analysis/COMPARISON.md")
        data["rows"][0].update(status="unknown", value=0, finding_ids=[])
        self.edit("analysis/COMPARISON.md", rows=data["rows"])
        self.assert_fail("must be null")

    def test_duplicate_yaml_keys(self):
        p = self.root / "findings/finding-price.md"
        p.write_text(p.read_text().replace("document_type: finding", "document_type: finding\ndocument_type: source"))
        self.assert_fail("unique strings")

    def test_alias_yaml(self):
        p = self.root / "findings/finding-price.md"
        p.write_text(p.read_text().replace("notes: Synthetic fixture", "notes: &x Synthetic fixture\nextra: *x"))
        self.assert_fail("aliases")

    def test_writer_omits_aliases_for_shared_values(self):
        shared = {"state": "SUPPORTED", "source_ids": ["source-price"]}
        path = self.root / "findings/writer-alias-check.md"
        write_document(path, {"left": shared, "right": shared}, "# Plain data\n")
        raw = path.read_text(encoding="utf-8")
        self.assertNotIn("&id", raw)
        self.assertNotIn("*id", raw)
        data, _ = read_document(path)
        self.assertEqual(data["left"], data["right"])

    def test_conflicting_evidence_preserved(self):
        finding, body = read_document(self.root / "findings/finding-price.md")
        finding["conflict_group_id"] = "conflict-price"
        write_document(self.root / "findings/finding-price.md", finding, body)
        other = copy.deepcopy(finding)
        other.update(finding_id="finding-price-other", normalized_value=3000000, source_ids=["source-other"])
        write_document(self.root / "findings/finding-price-other.md", other, body)
        source, body = read_document(self.root / "sources/source-price.md")
        source.update(source_id="source-other", url="https://sample.example.com/other",
                      canonical_url="https://sample.example.com/other", evidence_text="Synthetic conflicting price: 3000000 IRR.")
        source["content_sha256"] = hashlib.sha256(source["evidence_text"].encode()).hexdigest()
        write_document(self.root / "sources/source-other.md", source, body)
        self.edit("RUN.md", conflict_groups=[dict(conflict_group_id="conflict-price",
                  finding_ids=["finding-price", "finding-price-other"], interpretation="Conflicting fixture sources; unresolved.")])
        for rel in ("analysis/COMPARISON.md", "analysis/PRICING-ANALYSIS.md", "competitors/sample-optics/PRICING.md"):
            data, _ = read_document(self.root / rel)
            data["rows"][0].update(status="conflict", value=None, finding_ids=["finding-price", "finding-price-other"])
            self.edit(rel, rows=data["rows"])
        issues = seal(self.root)
        self.assertTrue(any(i["status"] == "WARNING" for i in issues))
        self.assertFalse(any(i["status"] == "FAIL" for i in issues))
        self.assertTrue(build(self.root).exists())

    def test_previous_run_change_tracking(self):
        previous = make_package(self.base / "previous", "previous-package", price=2000000)
        data = compare(previous, self.root)
        self.assertEqual(data["changes"][0]["change_type"], "pricing")
        self.assertEqual(data["changes"][0]["previous_value"][0]["value"], 2000000)
        write_document(self.root / "analysis/CHANGELOG.md", data, "# Changes\n\nSynthetic price change.\n")
        self.edit("RUN.md", previous_package_id="previous-package")
        seal(self.root)
        self.assertEqual(validate(self.root)[0], [])

    def test_no_previous_no_changelog(self):
        self.assertFalse((self.root / "analysis/CHANGELOG.md").exists())
        self.edit("RUN.md", previous_package_id="invented")
        self.assert_fail("changelog/previous-run mismatch")

    def test_bad_cross_entity_source(self):
        self.edit("sources/source-price.md", competitor_id="example-optics")
        self.assert_fail("source belongs to another entity")

    def test_search_snippet_cannot_support_fact(self):
        self.edit("sources/source-price.md", source_type="search_snippet")
        self.assert_fail("cannot support a factual finding")

    def test_third_party_strength(self):
        self.edit("sources/source-price.md", source_type="third_party")
        self.assert_fail("non-primary claim must be weak")

    def test_fail_report_cannot_be_import_ready(self):
        self.edit("VALIDATION.md", result="FAIL")
        self.assert_fail("failed package cannot be import_ready")

    def test_chart_value_must_match_finding(self):
        data, _ = read_document(self.root / "analysis/COMPARISON.md")
        data["rows"][0]["value"] = 1
        self.edit("analysis/COMPARISON.md", rows=data["rows"])
        self.assert_fail("chart value contradicts evidence")

    def test_malformed_frontmatter_fails_without_crash(self):
        self.edit("COMPETITORS.md", competitors={"wrong": "shape"})
        issues, _ = validate(self.root)
        self.assertTrue(any(i["status"] == "FAIL" for i in issues))

    def test_missing_derived_formula(self):
        self.edit("analysis/COMPARISON.md", derived_metrics=[dict(field_key="channel_count",
                  entity_id="sample-optics", value=1, unit="channels", inputs=["finding-price"], limitations=["sample"])])
        self.assert_fail("missing formula")

    def test_copied_skill_cli_and_zip_roundtrip(self):
        original = Path(__file__).parent.parent
        copied = self.base / "installed-skill"
        shutil.copytree(original, copied, ignore=shutil.ignore_patterns("__pycache__"))
        for script, args in (("validate_package.py", [str(self.root)]),
                             ("build_package.py", [str(self.root), "--output", str(self.base / "portable.zip")])):
            result = subprocess.run([sys.executable, str(copied / "scripts" / script), *args],
                                    cwd=self.base, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with zipfile.ZipFile(self.base / "portable.zip") as archive:
            archive.extractall(self.base / "extracted")
        self.assertEqual(validate(self.base / "extracted/competitor-intelligence-package")[0], [])

    def test_missing_snapshot_is_not_inactivity(self):
        previous = make_package(self.base / "previous", "previous-package")
        (self.root / "findings/finding-price.md").unlink()
        for path in self.root.rglob("*.md"):
            data, body = read_document(path)
            if data.get("document_type") in {"analysis", "company"} or str(data.get("document_type")).startswith("competitor_"):
                data["finding_ids"] = []
                if "rows" in data:
                    data["rows"] = []
                write_document(path, data, body)
        directory, body = read_document(self.root / "COMPETITORS.md")
        directory["competitors"][0]["verification_status"] = "candidate"
        directory["competitors"][0]["relevance_finding_ids"] = []
        write_document(self.root / "COMPETITORS.md", directory, body)
        profile, body = read_document(self.root / "competitors/sample-optics/PROFILE.md")
        profile["verification_status"] = "candidate"
        write_document(self.root / "competitors/sample-optics/PROFILE.md", profile, body)
        seal(self.root)
        result = compare(previous, self.root)
        self.assertEqual(result["changes"][0]["change_type"], "not_observed")

    def test_failed_seal_remains_draft(self):
        self.edit("findings/finding-price.md", review_status="approved")
        with self.assertRaises(ValueError):
            seal(self.root)
        manifest, _ = read_document(self.root / "MANIFEST.md")
        report, _ = read_document(self.root / "VALIDATION.md")
        self.assertEqual(manifest["package_status"], "draft")
        self.assertEqual(report["result"], "FAIL")

    def test_seal_generates_missing_validation_report(self):
        (self.root / "VALIDATION.md").unlink()
        self.assertEqual(seal(self.root), [])
        self.assertEqual(validate(self.root)[0], [])


if __name__ == "__main__":
    unittest.main()
