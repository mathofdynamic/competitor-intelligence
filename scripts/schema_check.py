"""Validate the small, documented JSON Schema subset used by this package contract."""
from __future__ import annotations

import json
from pathlib import Path

SCHEMA = json.loads((Path(__file__).parent.parent / "schemas/ci-package-v1.json").read_text())


def errors(value, schema, prefix="frontmatter"):
    if "$ref" in schema:
        schema = SCHEMA["$defs"][schema["$ref"].rsplit("/", 1)[-1]]
    typ = schema.get("type")
    kinds = {"object": lambda v: isinstance(v, dict), "array": lambda v: isinstance(v, list),
             "string": lambda v: isinstance(v, str), "integer": lambda v: type(v) is int,
             "boolean": lambda v: type(v) is bool}
    if typ and not kinds[typ](value):
        return [prefix + " must be " + typ]
    result = []
    if "const" in schema and value != schema["const"]:
        result.append(prefix + " has unsupported value")
    if "enum" in schema and value not in schema["enum"]:
        result.append(prefix + " has unsupported value")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                result.append(prefix + " missing " + key)
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                result.extend(errors(value[key], sub, prefix + "." + key))
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            result.append(prefix + " has too few items")
        for i, item in enumerate(value):
            result.extend(errors(item, schema.get("items", {}), f"{prefix}[{i}]"))
    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        result.append(prefix + " is empty")
    if type(value) is int and (value < schema.get("minimum", value) or value > schema.get("maximum", value)):
        result.append(prefix + " outside bounds")
    return result


def frontmatter_errors(data):
    result = errors(data, SCHEMA)
    typ = data.get("document_type", "")
    if typ.startswith("competitor_") and typ not in {"competitor_profile", "competitor_directory"}:
        typ = "dossier"
    if typ in SCHEMA["$defs"]:
        result.extend(errors(data, SCHEMA["$defs"][typ]))
    return result
