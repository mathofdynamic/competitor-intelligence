"""CI Markdown I/O, strict YAML loading, portable paths and manifest hashing."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath

try:
    import yaml
except ImportError as exc:
    raise SystemExit("Install dependencies: python -m pip install -r scripts/requirements.txt") from exc


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise ValueError("YAML keys must be unique strings")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def read_document(path: Path):
    if path.stat().st_size > 1_000_000:
        raise ValueError("document exceeds 1 MB")
    raw = path.read_bytes()
    return parse_document(raw)


def parse_document(raw: bytes):
    if len(raw) > 1_000_000:
        raise ValueError("document exceeds 1 MB")
    text = raw.decode("utf-8")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing YAML frontmatter")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise ValueError("unterminated YAML frontmatter")
    header = "".join(lines[1:end])
    # Aliases permit exponential expansion and identity ambiguity; package records use plain data.
    if any(isinstance(t, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken, yaml.tokens.TagToken))
           for t in yaml.scan(header)):
        raise ValueError("YAML aliases, anchors and explicit tags are unsupported")
    data = yaml.load(header, Loader=UniqueLoader)
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a mapping")
    return data, "".join(lines[end + 1:])


def write_document(path: Path, data: dict, body: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
                    + "---\n" + body, encoding="utf-8", newline="\n")


def portable_path(value: str) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    p = PurePosixPath(value)
    if p.is_absolute() or str(p) != value:
        return False
    return all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", part)
               and part not in {".", "..", "_work"}
               and part.split(".")[0].upper() not in
               {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)],
                *[f"LPT{i}" for i in range(1, 10)]}
               and not part.endswith(".") for part in p.parts)


def digest(path: Path, raw: bytes | None = None) -> str:
    raw = path.read_bytes() if raw is None else raw
    if path.name == "MANIFEST.md":
        data, body = parse_document(raw)
        # A manifest cannot contain its own ordinary byte hash. Only its own hash is blanked.
        for entry in data.get("files", []):
            if entry.get("path") == "MANIFEST.md":
                entry["sha256"] = ""
        raw = json.dumps({"frontmatter": data, "body": body}, ensure_ascii=False,
                         sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
