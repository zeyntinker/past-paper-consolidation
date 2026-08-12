#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from common import load_json, save_json


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def extract_document_text(docx_path: Path) -> tuple[str, int]:
    with zipfile.ZipFile(docx_path) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    chunks: list[str] = []

    def walk(element: ElementTree.Element) -> None:
        local = element.tag.rsplit("}", 1)[-1]
        if element.tag == f"{{{W_NS}}}t" and element.text:
            chunks.append(element.text)
        elif local in {"br", "cr"}:
            chunks.append("\n")
        elif local == "tab":
            chunks.append("\t")
        for child in element:
            walk(child)
        if local in {"p", "tr"}:
            chunks.append("\n")

    walk(root)
    drawing_count = len(root.findall(f".//{{{A_NS}}}blip"))
    return "".join(chunks), drawing_count


def verify_docx(docx_path: Path, ledger: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    text, drawing_count = extract_document_text(docx_path)
    questions = ledger.get("question_occurrences", [])
    images = ledger.get("images", [])

    for required_heading in (
        "제1부. 강의 순서 단권화",
        "제2부. 작년 기출 실전 순서",
        "제3부. 완전성 감사표",
    ):
        if required_heading not in text:
            errors.append(f"missing required heading: {required_heading}")

    for question in questions:
        question_id = question.get("id", "<missing>")
        if question_id not in text:
            errors.append(f"missing question ID in DOCX: {question_id}")
        for field in ("original_problem", "original_answer", "original_explanation"):
            value = question.get(field, "")
            if value and value not in text:
                errors.append(f"missing exact {field} for {question_id}")
        for index, choice in enumerate(question.get("original_choices", []), start=1):
            if choice and choice not in text:
                errors.append(f"missing exact choice {index} for {question_id}")

    included_images = 0
    for image in images:
        image_id = image.get("id", "<missing>")
        if image.get("word_location"):
            included_images += 1
            if image_id not in text:
                errors.append(f"missing image caption/ID in DOCX: {image_id}")
        elif image.get("status") != "review_required":
            errors.append(f"image lacks Word location and review status: {image_id}")
    if drawing_count < included_images:
        errors.append(
            f"DOCX contains {drawing_count} drawings but ledger expects at least {included_images} included images"
        )

    part_two = text.find("제2부. 작년 기출 실전 순서")
    part_three = text.find("제3부. 완전성 감사표")
    if part_two >= 0 and part_three > part_two:
        prior_text = text[part_two:part_three]
        previous = -1
        for entry in ledger.get("prior_year_sequence", []):
            question_ids = entry.get("question_ids", [])
            positions = [prior_text.find(question_id) for question_id in question_ids]
            if any(position < 0 for position in positions):
                errors.append(f"prior-year entry {entry.get('sequence')} is missing question IDs")
                continue
            current = min(positions)
            if current <= previous:
                errors.append("prior-year question order differs from ledger")
                break
            previous = current

    blocking = [
        finding
        for finding in ledger.get("audit_findings", [])
        if finding.get("severity") == "blocking" and finding.get("status") != "resolved"
    ]
    if blocking:
        errors.append(f"ledger still has {len(blocking)} unresolved blocking finding(s)")

    return {
        "valid": not errors,
        "status": "verified" if not errors else "review_required",
        "errors": errors,
        "counts": {
            "questions_expected": len(questions),
            "images_expected_in_docx": included_images,
            "drawings_found": drawing_count,
            "prior_year_entries": len(ledger.get("prior_year_sequence", [])),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Independently verify a generated master-note DOCX")
    parser.add_argument("docx")
    parser.add_argument("ledger")
    parser.add_argument("--report")
    args = parser.parse_args()
    report = verify_docx(Path(args.docx), load_json(args.ledger))
    if args.report:
        save_json(args.report, report)
    for error in report["errors"]:
        print(f"ERROR: {error}")
    print(report["status"])
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    sys.exit(main())
