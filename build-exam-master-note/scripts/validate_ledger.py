#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections import Counter
from typing import Any

from common import PROVENANCE_KINDS, ensure_unique, load_json, save_json


QUESTION_FIELDS = {
    "original_problem",
    "original_answer",
    "original_explanation",
}


def validate_provenance(
    component: dict[str, Any],
    questions: dict[str, dict[str, Any]],
    path: str,
) -> list[str]:
    errors: list[str] = []
    text = component.get("text")
    if not isinstance(text, str):
        errors.append(f"{path}.text must be a string")
    provenance = component.get("provenance")
    if not isinstance(provenance, list) or not provenance:
        return errors + [f"{path} has no provenance"]
    for index, source in enumerate(provenance):
        source_path = f"{path}.provenance[{index}]"
        kind = source.get("kind")
        if kind not in PROVENANCE_KINDS:
            errors.append(f"{source_path} has invalid kind: {kind}")
            continue
        if kind == "original":
            question_id = source.get("source_question_id")
            field = source.get("source_field")
            question = questions.get(question_id)
            if not question:
                errors.append(f"{source_path} references unknown question {question_id}")
            elif field == "original_choices":
                choice_index = source.get("choice_index")
                choices = question.get("original_choices", [])
                if not isinstance(choice_index, int) or not 0 <= choice_index < len(choices):
                    errors.append(f"{source_path} has invalid choice_index")
                elif text != choices[choice_index]:
                    errors.append(f"{path} is labeled original but choice text changed")
            elif field not in QUESTION_FIELDS:
                errors.append(f"{source_path} has invalid source_field: {field}")
            elif question and text != question.get(field, ""):
                errors.append(f"{path} is labeled original but {field} text changed")
        elif kind == "ai_reconstruction_from_questions":
            source_ids = source.get("source_question_ids")
            if not source_ids or any(source_id not in questions for source_id in source_ids):
                errors.append(f"{source_path} lacks valid source_question_ids")
        elif kind == "lecture_note_supplement":
            if not source.get("source_artifact_id") or not source.get("source_page"):
                errors.append(f"{source_path} lacks lecture-note file/page")
        elif kind == "master_note_supplement":
            if not source.get("representative_type_id"):
                errors.append(f"{source_path} lacks representative_type_id")
        elif kind == "external_ai_supplement":
            if not source.get("citation") or not source.get("locator"):
                errors.append(f"{source_path} lacks authoritative citation/locator")
        elif kind == "source_unverified":
            errors.append(f"{source_path} remains source_unverified")
    return errors


def validate_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    sources = ledger.get("source_artifacts", [])
    occurrences = ledger.get("question_occurrences", [])
    images = ledger.get("images", [])
    representatives = ledger.get("representative_types", [])
    findings = ledger.get("audit_findings", [])

    errors.extend(ensure_unique(sources, "source_artifact"))
    errors.extend(ensure_unique(occurrences, "question_occurrence"))
    errors.extend(ensure_unique(images, "image"))
    errors.extend(ensure_unique(representatives, "representative_type"))
    errors.extend(ensure_unique(findings, "audit_finding"))

    source_ids = {record.get("id") for record in sources}
    questions = {record.get("id"): record for record in occurrences if record.get("id")}
    image_ids = {record.get("id") for record in images}
    representative_ids = {record.get("id") for record in representatives}

    if not ledger.get("manifest_fingerprint"):
        errors.append("ledger has no manifest_fingerprint")
    if ledger.get("manifest_fingerprint") != ledger.get("approved_manifest_fingerprint"):
        errors.append("ledger manifest fingerprint does not match approved manifest fingerprint")

    required_source_fields = {
        "id",
        "logical_artifact_id",
        "file_name",
        "format",
        "sha256",
        "size_bytes",
        "source_role",
        "source_link_index",
        "page_count",
        "processed_pages",
        "status",
    }
    for source in sources:
        source_id = source.get("id", "<missing>")
        missing = sorted(required_source_fields - set(source))
        if missing:
            errors.append(f"{source_id} is missing source fields: {missing}")
            continue
        page_count = source.get("page_count")
        if not isinstance(page_count, int) or page_count < 1:
            errors.append(f"{source_id}.page_count must be a positive integer")
        elif source.get("processed_pages") != list(range(1, page_count + 1)):
            errors.append(f"{source_id} does not account for every physical page")
        if len(str(source.get("sha256", ""))) != 64:
            errors.append(f"{source_id}.sha256 is invalid")
        if source.get("status") not in {"normalized", "verified"}:
            errors.append(f"{source_id} is not normalized/verified")

    for question in occurrences:
        question_id = question.get("id", "<missing>")
        if question.get("source_artifact_id") not in source_ids:
            errors.append(f"{question_id} references unknown source artifact")
        for field in QUESTION_FIELDS:
            if not isinstance(question.get(field), str):
                errors.append(f"{question_id}.{field} must be a string")
        if not isinstance(question.get("original_choices"), list):
            errors.append(f"{question_id}.original_choices must be a list")
        linked_rep = question.get("representative_type_id")
        review_queue = question.get("review_queue_id")
        if bool(linked_rep) == bool(review_queue):
            errors.append(
                f"{question_id} must link to exactly one representative_type_id or review_queue_id"
            )
        if linked_rep and linked_rep not in representative_ids:
            errors.append(f"{question_id} references unknown representative type {linked_rep}")
        if not question.get("word_location"):
            errors.append(f"{question_id} has no Word location")
        for image_id in question.get("image_ids", []):
            if image_id not in image_ids:
                errors.append(f"{question_id} references unknown image {image_id}")

    linked_counts: Counter[str] = Counter()
    expected_lecture_order = list(range(1, len(representatives) + 1))
    actual_lecture_order = [item.get("lecture_order") for item in representatives]
    if actual_lecture_order != expected_lecture_order:
        errors.append("representative types are not in consecutive lecture_order")
    for representative in representatives:
        rep_id = representative.get("id", "<missing>")
        linked_ids = representative.get("question_ids", [])
        for question_id in linked_ids:
            linked_counts[question_id] += 1
            if question_id not in questions:
                errors.append(f"{rep_id} references unknown question {question_id}")
        for key in ("problem_components", "choice_components", "explanation_components"):
            components = representative.get(key)
            if not isinstance(components, list):
                errors.append(f"{rep_id}.{key} must be a list")
                continue
            for index, component in enumerate(components):
                component_path = f"{rep_id}.{key}[{index}]"
                errors.extend(validate_provenance(component, questions, component_path))
                if key == "choice_components":
                    if component.get("verdict") not in {"O", "X", "correct", "incorrect", "uncertain"}:
                        errors.append(f"{component_path} has no valid verdict")
                    rationales = component.get("rationale_components")
                    if not isinstance(rationales, list) or not rationales:
                        errors.append(f"{component_path} has no rationale")
                    else:
                        for r_index, rationale in enumerate(rationales):
                            errors.extend(
                                validate_provenance(
                                    rationale,
                                    questions,
                                    f"{component_path}.rationale_components[{r_index}]",
                                )
                            )

        if representative.get("question_type") in {"객관식", "objective", "multiple_choice"}:
            original_choices = {
                choice
                for question_id in linked_ids
                for choice in questions.get(question_id, {}).get("original_choices", [])
            }
            representative_choices = {
                component.get("text") for component in representative.get("choice_components", [])
            }
            missing = sorted(original_choices - representative_choices)
            if missing:
                errors.append(f"{rep_id} omits original objective choices: {missing}")

    for question in occurrences:
        question_id = question.get("id")
        if question.get("representative_type_id") and linked_counts[question_id] != 1:
            errors.append(
                f"{question_id} appears in {linked_counts[question_id]} representative types, expected 1"
            )

    for image in images:
        image_id = image.get("id", "<missing>")
        if image.get("source_artifact_id") not in source_ids:
            errors.append(f"{image_id} references unknown source artifact")
        for question_id in image.get("question_ids", []):
            if question_id not in questions:
                errors.append(f"{image_id} references unknown question {question_id}")
        if not image.get("word_location") and image.get("status") != "review_required":
            errors.append(f"{image_id} has no Word location or review status")
        provenance = image.get("provenance")
        if not isinstance(provenance, list) or not provenance:
            errors.append(f"{image_id} has no provenance")
        else:
            for source in provenance:
                if source.get("kind") not in PROVENANCE_KINDS:
                    errors.append(f"{image_id} has invalid provenance kind")
                if source.get("kind") == "original" and source.get("source_image_id") != image_id:
                    errors.append(f"{image_id} original provenance does not point to itself")

    previous_sequence = 0
    for entry in ledger.get("prior_year_sequence", []):
        sequence = entry.get("sequence")
        if not isinstance(sequence, int) or sequence != previous_sequence + 1:
            errors.append("prior_year_sequence is not consecutive from 1")
            break
        previous_sequence = sequence
        for question_id in entry.get("question_ids", []):
            if question_id not in questions:
                errors.append(f"prior-year sequence references unknown question {question_id}")
        for index, component in enumerate(entry.get("supplement_components", [])):
            errors.extend(
                validate_provenance(component, questions, f"prior_year_sequence[{sequence}].supplement[{index}]")
            )

    blocking = [
        finding
        for finding in findings
        if finding.get("severity") == "blocking" and finding.get("status") != "resolved"
    ]
    if blocking:
        errors.append(f"{len(blocking)} unresolved blocking audit finding(s)")

    return {
        "valid": not errors,
        "status": "complete_candidate" if not errors else "review_required",
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "source_artifacts": len(sources),
            "question_occurrences": len(occurrences),
            "images": len(images),
            "representative_types": len(representatives),
            "prior_year_sequence": len(ledger.get("prior_year_sequence", [])),
            "audit_findings": len(findings),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate provenance and completeness ledger")
    parser.add_argument("ledger")
    parser.add_argument("--report")
    args = parser.parse_args()
    report = validate_ledger(load_json(args.ledger))
    if args.report:
        save_json(args.report, report)
    for error in report["errors"]:
        print(f"ERROR: {error}")
    print(report["status"])
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    sys.exit(main())
