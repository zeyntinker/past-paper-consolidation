#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


SUPPORTED_EXTENSIONS = {".pdf", ".hwp", ".hwpx"}
PROVENANCE_KINDS = {
    "original",
    "ai_reconstruction_from_questions",
    "lecture_note_supplement",
    "master_note_supplement",
    "external_ai_supplement",
    "source_unverified",
}

SEMANTIC_ATOM_CATEGORIES = {
    "problem",
    "original_explanation",
    "lecture_note",
    "external_supplement",
}
SEMANTIC_RELEVANCE_STATUSES = {"required", "excluded", "review_required"}
SEMANTIC_TARGET_KINDS = {
    "problem_component",
    "choice_component",
    "answer_component",
    "rationale_component",
    "explanation_component",
}
SEMANTIC_INTEGRATION_MODES = {
    "exact",
    "synthesized",
    "duplicate_merged",
    "conditional_split",
}


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("\x1f".join(map(str, parts)).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:12].upper()}"


def ensure_unique(records: list[dict[str, Any]], label: str) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for index, record in enumerate(records):
        record_id = record.get("id")
        if not record_id:
            errors.append(f"{label}[{index}] is missing id")
        elif record_id in seen:
            errors.append(f"duplicate {label} id: {record_id}")
        else:
            seen.add(record_id)
    return errors
