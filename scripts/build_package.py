"""Seal an authored package or build a validated, manifest-only ZIP."""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from package_io import digest, portable_path, read_document, write_document
from validate_package import expected_type, validate


def seal(root: Path):
    """Explicit authoring operation; never used implicitly by the ZIP builder."""
    if not root.is_dir() or root.is_symlink() or (hasattr(root, "is_junction") and root.is_junction()):
        raise ValueError("package must be a real directory")
    for path in root.rglob("*"):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()) or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("linked or escaped paths forbidden")
        if not portable_path(path.relative_to(root).as_posix()):
            raise ValueError("unsafe path")
    manifest, body = read_document(root / "MANIFEST.md")
    report = {k: manifest[k] for k in ("schema_version", "package_id", "run_id")}
    report.update(document_type="validation", generated_at=datetime.now(timezone.utc).isoformat(),
                  result="WARNING", checks=[], validator="ci-package/v1 local validator", hash_check="pending")
    write_document(root / "VALIDATION.md", report, "# Validation\n\nPending authoring validation.\n")
    inventory = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("symlinks forbidden")
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            typ = expected_type(rel)
            if not typ:
                raise ValueError("file outside contract: " + rel)
            inventory.append({"path": rel, "document_type": typ, "sha256": "0" * 64})
    directory, _ = read_document(root / "COMPETITORS.md")
    competitors = [c for c in directory["competitors"] if c["classification"] != "excluded"]
    manifest.update(files=inventory, file_count=len(inventory), competitor_count=len(competitors),
                    direct_competitor_count=sum(c["classification"] == "direct" for c in competitors),
                    source_count=sum(e["document_type"] == "source" for e in inventory),
                    finding_count=sum(e["document_type"] == "finding" for e in inventory),
                    package_status="draft")
    write_document(root / "MANIFEST.md", manifest, body)
    issues, _ = validate(root, check_hashes=False)
    failed = any(i["status"] == "FAIL" for i in issues)
    report.update(document_type="validation", generated_at=datetime.now(timezone.utc).isoformat(),
                  result="FAIL" if failed else "WARNING" if issues else "PASS", checks=issues,
                  validator="ci-package/v1 local validator", hash_check="verified after sealing")
    write_document(root / "VALIDATION.md", report,
                   "# Validation\n\n" + report["result"] + "\n\n" +
                   "\n".join(f"- {i['status']}: {i['path']}: {i['message']}" for i in issues) +
                   "\n\nStructural validation cannot establish factual truth. All findings need human review.\n")
    manifest["package_status"] = "draft" if failed else "import_ready"
    for entry in inventory:
        if entry["path"] != "MANIFEST.md":
            entry["sha256"] = digest(root / entry["path"])
    write_document(root / "MANIFEST.md", manifest, body)
    for entry in inventory:
        if entry["path"] == "MANIFEST.md":
            entry["sha256"] = digest(root / "MANIFEST.md")
    write_document(root / "MANIFEST.md", manifest, body)
    final, _ = validate(root)
    if any(i["status"] == "FAIL" for i in final):
        manifest["package_status"] = "draft"
        report.update(result="FAIL", checks=final, hash_check="failed")
        write_document(root / "VALIDATION.md", report, "# Validation\n\nFAIL. Resolve reported checks before sealing again.\n")
        for entry in inventory:
            if entry["path"] == "VALIDATION.md":
                entry["sha256"] = digest(root / "VALIDATION.md")
        write_document(root / "MANIFEST.md", manifest, body)
        for entry in inventory:
            if entry["path"] == "MANIFEST.md":
                entry["sha256"] = digest(root / "MANIFEST.md")
        write_document(root / "MANIFEST.md", manifest, body)
        raise ValueError("package failed validation: " + str(final))
    return final


def build(root: Path, output: Path | None = None):
    issues, records = validate(root)
    if any(i["status"] == "FAIL" for i in issues):
        raise ValueError("ZIP refused: " + str(issues))
    manifest = records["MANIFEST.md"]
    if manifest["package_status"] != "import_ready":
        raise ValueError("ZIP refused: package is not import_ready; author and seal it first")
    company = re.sub(r"[^a-z0-9-]+", "-", manifest["company_id"].lower()).strip("-")
    date = manifest["research_finished_at"][:10]
    output = output or root.parent / f"{company}-competitor-intelligence-{date}.zip"
    if output.resolve().is_relative_to(root.resolve()):
        raise ValueError("ZIP output must be outside package")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError("output already exists; choose another --output")
    fd, tmp_name = tempfile.mkstemp(prefix=".ci-", suffix=".zip", dir=output.parent)
    os.close(fd)
    temp = Path(tmp_name)
    try:
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for entry in manifest["files"]:
                path = root / entry["path"]
                # Read each file once after validation; verify those exact bytes before writing.
                if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != root.parent):
                    raise ValueError("symlink detected during packaging")
                raw = path.read_bytes()
                actual = digest(path, raw) if entry["path"] == "MANIFEST.md" else hashlib.sha256(raw).hexdigest()
                if actual != entry["sha256"]:
                    raise ValueError("file changed during packaging: " + entry["path"])
                archive.writestr("competitor-intelligence-package/" + entry["path"], raw)
        # Exclusive destination prevents replacing an existing artifact.
        created_output = False
        try:
            with output.open("xb") as destination, temp.open("rb") as source:
                created_output = True
                shutil.copyfileobj(source, destination)
        except Exception:
            if created_output:
                output.unlink(missing_ok=True)
            raise
    finally:
        temp.unlink(missing_ok=True)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_dir", type=Path)
    parser.add_argument("--seal", action="store_true", help="authoring: refresh manifest and VALIDATION.md; does not build ZIP")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.seal:
            if args.output:
                raise ValueError("--output cannot be used with --seal")
            issues = seal(args.package_dir)
            print("sealed: " + ("WARNING" if issues else "PASS"))
        else:
            output = build(args.package_dir, args.output)
            checksum = hashlib.sha256()
            with output.open("rb") as artifact:
                for chunk in iter(lambda: artifact.read(65536), b""):
                    checksum.update(chunk)
            print(output)
            print("SHA-256: " + checksum.hexdigest())
    except Exception as exc:
        print("FAIL: " + str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
