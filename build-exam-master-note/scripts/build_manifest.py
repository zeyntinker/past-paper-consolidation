#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from common import SUPPORTED_EXTENSIONS, fingerprint, load_json, save_json, stable_id


DATE_RE = re.compile(r"(?<!\d)(?P<date>\d{6})(?!\d)")
YEAR_RE = re.compile(r"(?<!\d)(20\d{2})(?!\d)")
PERIOD_RE = re.compile(r"(?<!\d)(\d{1,2})\s*교시")


def decode_link(link: str) -> str:
    return urllib.parse.unquote(link)


def infer_current_year(link: str) -> int | None:
    match = YEAR_RE.search(decode_link(link))
    return int(match.group(1)) if match else None


def parse_filename_date(name: str) -> str | None:
    match = DATE_RE.search(name)
    if not match:
        return None
    raw = match.group("date")
    year = 2000 + int(raw[:2])
    try:
        return date(year, int(raw[2:4]), int(raw[4:6])).isoformat()
    except ValueError:
        return None


def parse_period(first_page_text: str | None) -> int | None:
    if not first_page_text:
        return None
    match = PERIOD_RE.search(first_page_text)
    return int(match.group(1)) if match else None


def validate_direct_item(item: dict[str, Any], link_index: int) -> str | None:
    name = str(item.get("name", "")).strip()
    relative = str(item.get("relative_path", name)).strip()
    if not name:
        return f"link {link_index} contains an item with no name"
    if relative != name or "/" in relative or "\\" in relative or relative in {".", ".."}:
        return f"link {link_index} item is not a direct child: {relative}"
    return None


def normalized_stem(name: str) -> str:
    stem = Path(name).stem.casefold()
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem


def prior_year_match(name: str, prior_year: int) -> bool:
    short = str(prior_year)[2:]
    return bool(
        re.search(rf"(?<!\d){prior_year}(?!\d)", name)
        or re.search(rf"(?<!\d){short}\d{{4}}(?!\d)", name)
    )


def classify_prior_role(name: str) -> list[str]:
    roles: list[str] = []
    if "복기" in name or "기출문제" in name or "기출 문제" in name:
        roles.append("reconstruction_order_source")
    if "해설" in name or "정리" in name:
        roles.append("explanation_source")
    if not roles:
        roles.append("candidate_source")
    return roles


def build_manifest(inventory: dict[str, Any]) -> dict[str, Any]:
    first_link = inventory.get("first_link")
    second_link = inventory.get("second_link")
    if not first_link or not second_link:
        raise ValueError("inventory must contain first_link and second_link")

    current_year = inventory.get("current_year") or infer_current_year(first_link)
    if not current_year:
        raise ValueError("could not infer current year from first link; provide current_year")
    current_year = int(current_year)
    prior_year = current_year - 1
    exam_scope = str(inventory.get("exam_scope") or "").strip()

    included: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []

    for link_index, key in ((1, "first_link_items"), (2, "second_link_items")):
        for item in inventory.get(key, []):
            direct_error = validate_direct_item(item, link_index)
            if direct_error:
                findings.append(
                    {
                        "id": stable_id("F", direct_error),
                        "severity": "blocking",
                        "code": "OUTSIDE_DIRECT_LINK_SCOPE",
                        "message": direct_error,
                        "source_locations": [item.get("relative_path", item.get("name", ""))],
                        "status": "open",
                    }
                )
                continue

            name = str(item["name"])
            extension = Path(name).suffix.casefold()
            base = {
                "id": stable_id("FILE", link_index, name),
                "name": name,
                "relative_path": name,
                "extension": extension,
                "size_bytes": int(item.get("size_bytes") or 0),
                "link_index": link_index,
                "logical_stem": normalized_stem(name),
            }

            if extension not in SUPPORTED_EXTENSIONS:
                excluded.append({**base, "reason": "unsupported_file_type"})
                continue
            if link_index == 1 and "합본" in name:
                excluded.append({**base, "reason": "contains_합본"})
                continue
            if link_index == 2 and not prior_year_match(name, prior_year):
                excluded.append({**base, "reason": f"not_prior_year_{prior_year}"})
                continue
            if link_index == 2 and exam_scope and exam_scope.casefold() not in name.casefold():
                # Exam scope may be expressed inside content rather than filename. Keep as a
                # blocking candidate instead of silently dropping it.
                findings.append(
                    {
                        "id": stable_id("F", name, "scope"),
                        "severity": "blocking",
                        "code": "EXAM_SCOPE_REQUIRES_CONFIRMATION",
                        "message": f"Confirm that {name} belongs to exam scope {exam_scope}",
                        "source_locations": [name],
                        "status": "open",
                    }
                )

            if link_index == 1:
                parsed_date = parse_filename_date(name)
                period = parse_period(item.get("first_page_text"))
                record = {
                    **base,
                    "source_roles": ["current_lecture_past_paper"],
                    "lecture_date": parsed_date,
                    "period": period,
                }
                if parsed_date is None:
                    findings.append(
                        {
                            "id": stable_id("F", name, "date"),
                            "severity": "blocking",
                            "code": "DATE_UNREADABLE",
                            "message": f"Could not parse lecture date from {name}",
                            "source_locations": [name],
                            "status": "open",
                        }
                    )
                if period is None:
                    findings.append(
                        {
                            "id": stable_id("F", name, "period"),
                            "severity": "blocking",
                            "code": "PERIOD_UNREADABLE",
                            "message": f"Could not parse period from first page of {name}",
                            "source_locations": [name, "page 1"],
                            "status": "open",
                        }
                    )
                included.append(record)
            else:
                included.append(
                    {
                        **base,
                        "source_roles": classify_prior_role(name),
                        "prior_year": prior_year,
                    }
                )

    groups: dict[tuple[int, str], list[str]] = defaultdict(list)
    for item in included:
        groups[(item["link_index"], item["logical_stem"])].append(item["id"])
    logical_artifacts = [
        {
            "id": stable_id("ART", link_index, stem),
            "link_index": link_index,
            "logical_stem": stem,
            "file_ids": sorted(file_ids),
        }
        for (link_index, stem), file_ids in sorted(groups.items())
    ]
    group_id = {
        file_id: group["id"]
        for group in logical_artifacts
        for file_id in group["file_ids"]
    }
    for item in included:
        item["logical_artifact_id"] = group_id[item["id"]]

    first_items = [item for item in included if item["link_index"] == 1]
    first_items.sort(
        key=lambda item: (
            item.get("lecture_date") or "9999-99-99",
            item.get("period") is None,
            item.get("period") if item.get("period") is not None else 999,
            item["name"].casefold(),
        )
    )
    prior_items = sorted(
        (item for item in included if item["link_index"] == 2),
        key=lambda item: item["name"].casefold(),
    )
    ordered = first_items + prior_items
    for index, item in enumerate(ordered, start=1):
        item["manifest_order"] = index

    manifest_core = {
        "schema_version": 1,
        "first_link": first_link,
        "second_link": second_link,
        "exploration_policy": "direct_children_only",
        "current_year": current_year,
        "prior_year": prior_year,
        "exam_scope": exam_scope,
        "included_files": ordered,
        "excluded_files": sorted(excluded, key=lambda item: (item["link_index"], item["name"])),
        "logical_artifacts": logical_artifacts,
        "audit_findings": findings,
    }
    manifest_core["inventory_fingerprint"] = fingerprint(manifest_core)
    manifest_core["approval"] = {
        "status": "required",
        "approved_fingerprint": None,
    }
    return manifest_core


def approve_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    expected = fingerprint(
        {key: value for key, value in manifest.items() if key not in {"approval", "inventory_fingerprint"}}
    )
    if manifest.get("inventory_fingerprint") != expected:
        raise ValueError("manifest content changed after fingerprinting; rebuild before approval")
    approved = dict(manifest)
    approved["approval"] = {
        "status": "approved",
        "approved_fingerprint": manifest["inventory_fingerprint"],
    }
    return approved


def verify_approval(manifest: dict[str, Any]) -> bool:
    approval = manifest.get("approval", {})
    expected = fingerprint(
        {key: value for key, value in manifest.items() if key not in {"approval", "inventory_fingerprint"}}
    )
    return (
        manifest.get("inventory_fingerprint") == expected
        and
        approval.get("status") == "approved"
        and approval.get("approved_fingerprint") == manifest.get("inventory_fingerprint")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and approve a fail-closed source manifest")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("inventory")
    build_parser.add_argument("--out", required=True)

    approve_parser = subparsers.add_parser("approve")
    approve_parser.add_argument("manifest")
    approve_parser.add_argument("--out", required=True)

    verify_parser = subparsers.add_parser("verify-approval")
    verify_parser.add_argument("manifest")

    args = parser.parse_args()
    if args.command == "build":
        save_json(args.out, build_manifest(load_json(args.inventory)))
        return 0
    if args.command == "approve":
        save_json(args.out, approve_manifest(load_json(args.manifest)))
        return 0
    valid = verify_approval(load_json(args.manifest))
    print("approved" if valid else "approval_invalid")
    return 0 if valid else 2


if __name__ == "__main__":
    sys.exit(main())
