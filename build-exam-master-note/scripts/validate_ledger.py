#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from typing import Any

from common import (
    PROVENANCE_KINDS,
    SEMANTIC_ATOM_CATEGORIES,
    SEMANTIC_INTEGRATION_MODES,
    SEMANTIC_RELEVANCE_STATUSES,
    SEMANTIC_TARGET_KINDS,
    ensure_unique,
    load_json,
    save_json,
)


QUESTION_FIELDS = {
    "original_problem",
    "original_answer",
    "original_explanation",
}

PROBLEM_TARGETS = {"problem_component", "choice_component"}
EXPLANATION_TARGETS = {"answer_component", "rationale_component", "explanation_component"}


def substantive_text(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = re.sub(r"\s+", " ", value).strip()
    if not text:
        return False
    shells = (
        r"^-?\s*\d+\s*-?$",
        r"^(문제|문항)\s*\d*\s*[.)-]?$",
        r"^(해설|정답|답)\s*(참조|확인)?\s*$",
        r"^(교과서|족보|강의안|자료)\s*(참조|확인)\s*$",
    )
    return not any(re.fullmatch(pattern, text, flags=re.IGNORECASE) for pattern in shells)


def representative_components(
    representative: dict[str, Any],
    rep_id: str,
    errors: list[str],
) -> dict[str, str]:
    components: dict[str, str] = {}

    def register(component: dict[str, Any], kind: str, path: str) -> None:
        component_id = component.get("id")
        if not component_id:
            errors.append(f"{path} is missing internal component id")
        elif component_id in components:
            errors.append(f"duplicate component id in {rep_id}: {component_id}")
        else:
            components[component_id] = kind

    for field, kind in (
        ("problem_components", "problem_component"),
        ("choice_components", "choice_component"),
        ("answer_components", "answer_component"),
        ("explanation_components", "explanation_component"),
    ):
        field_components = representative.get(field, [])
        if not isinstance(field_components, list):
            continue
        for index, component in enumerate(field_components):
            if not isinstance(component, dict):
                errors.append(f"{rep_id}.{field}[{index}] must be an object")
                continue
            register(component, kind, f"{rep_id}.{field}[{index}]")
            if field == "choice_components":
                rationales = component.get("rationale_components", [])
                if not isinstance(rationales, list):
                    continue
                for r_index, rationale in enumerate(rationales):
                    if not isinstance(rationale, dict):
                        errors.append(f"{rep_id}.{field}[{index}].rationale_components[{r_index}] must be an object")
                        continue
                    register(
                        rationale,
                        "rationale_component",
                        f"{rep_id}.{field}[{index}].rationale_components[{r_index}]",
                    )
    return components


def validate_semantic_completeness(
    ledger: dict[str, Any],
    representatives: list[dict[str, Any]],
    questions: dict[str, dict[str, Any]],
    sources: dict[str, dict[str, Any]],
    images: set[str],
    component_maps: dict[str, dict[str, str]],
) -> tuple[list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    atoms = ledger.get("semantic_atoms", [])
    coverage = ledger.get("semantic_coverage", [])
    reviews = ledger.get("second_pass_reviews", [])
    for field_name, value in (
        ("semantic_atoms", atoms),
        ("semantic_coverage", coverage),
        ("second_pass_reviews", reviews),
    ):
        if not isinstance(value, list):
            errors.append(f"{field_name} must be a list")
    atoms = atoms if isinstance(atoms, list) else []
    coverage = coverage if isinstance(coverage, list) else []
    reviews = reviews if isinstance(reviews, list) else []
    if ledger.get("schema_version") != 2:
        errors.append("semantic completeness requires schema_version 2")
    errors.extend(ensure_unique(atoms, "semantic_atom"))
    errors.extend(ensure_unique(coverage, "semantic_coverage"))
    errors.extend(ensure_unique(reviews, "second_pass_review"))

    representative_ids = {item.get("id") for item in representatives}
    atom_by_id = {item.get("id"): item for item in atoms if item.get("id")}
    coverage_by_atom: dict[str, list[dict[str, Any]]] = {}
    reviews_by_rep: dict[str, list[dict[str, Any]]] = {}
    duplicate_groups: dict[str, list[str]] = {}
    conflict_groups: dict[str, list[str]] = {}
    invalid_coverage_atoms: set[str] = set()

    for atom in atoms:
        atom_id = atom.get("id", "<missing>")
        rep_id = atom.get("representative_type_id")
        if rep_id not in representative_ids:
            errors.append(f"{atom_id} references unknown representative {rep_id}")
        if atom.get("category") not in SEMANTIC_ATOM_CATEGORIES:
            errors.append(f"{atom_id} has invalid semantic category")
        if not atom.get("atom_type"):
            errors.append(f"{atom_id} has no atom_type")
        if atom.get("provenance_kind") not in PROVENANCE_KINDS:
            errors.append(f"{atom_id} has invalid provenance_kind")
        relevance = atom.get("relevance_status")
        if relevance not in SEMANTIC_RELEVANCE_STATUSES:
            errors.append(f"{atom_id} has invalid relevance_status")
        if relevance == "excluded" and not atom.get("exclusion_reason"):
            errors.append(f"{atom_id} excluded without a reason")
        if relevance == "review_required":
            errors.append(f"{atom_id} still has ambiguous relevance")
        if relevance == "required" and atom.get("status") != "verified":
            errors.append(f"{atom_id} is required but not verified")
        source_id = atom.get("source_artifact_id")
        source = sources.get(source_id)
        source_page = atom.get("source_page")
        if atom.get("category") == "external_supplement":
            if atom.get("provenance_kind") != "external_ai_supplement":
                errors.append(f"{atom_id} external atom has wrong provenance_kind")
            if not atom.get("citation") or not atom.get("locator"):
                errors.append(f"{atom_id} external atom lacks authoritative citation/locator")
        elif not source:
            errors.append(f"{atom_id} references unknown source artifact {source_id}")
        elif (
            not isinstance(source_page, int)
            or not isinstance(source.get("page_count"), int)
            or not 1 <= source_page <= source.get("page_count")
        ):
            errors.append(f"{atom_id} has invalid source page")
        if not atom.get("text") and atom.get("image_id") not in images:
            errors.append(f"{atom_id} has neither source text nor a valid image")
        if relevance == "required" and atom.get("provenance_kind") == "source_unverified":
            errors.append(f"{atom_id} remains source_unverified")
        question_id = atom.get("source_question_id")
        if question_id:
            question = questions.get(question_id)
            if not question:
                errors.append(f"{atom_id} references unknown source question {question_id}")
            elif question.get("source_artifact_id") != source_id or question.get("source_page") != source_page:
                errors.append(f"{atom_id} source locator disagrees with {question_id}")
            else:
                field = atom.get("source_field")
                source_text = ""
                if field == "original_choices":
                    choice_index = atom.get("choice_index")
                    choices = question.get("original_choices", [])
                    if not isinstance(choice_index, int) or not 0 <= choice_index < len(choices):
                        errors.append(f"{atom_id} has invalid choice_index")
                    else:
                        source_text = choices[choice_index]
                elif field in QUESTION_FIELDS:
                    source_text = question.get(field, "")
                else:
                    errors.append(f"{atom_id} has invalid question source_field: {field}")
                if atom.get("text") and atom.get("text") not in source_text:
                    errors.append(f"{atom_id} text is not exact source text")
        if atom.get("category") == "original_explanation":
            if question_id not in questions or atom.get("source_field") not in {
                "original_answer",
                "original_explanation",
            }:
                errors.append(f"{atom_id} lacks an original answer/explanation source field")
        image_id = atom.get("image_id")
        if image_id:
            image = next((item for item in ledger.get("images", []) if item.get("id") == image_id), None)
            if not image or image.get("source_artifact_id") != source_id or image.get("source_page") != source_page:
                errors.append(f"{atom_id} image locator is invalid")
        if atom.get("duplicate_group_id"):
            duplicate_groups.setdefault(atom["duplicate_group_id"], []).append(atom_id)
        if atom.get("conflict_group_id"):
            conflict_groups.setdefault(atom["conflict_group_id"], []).append(atom_id)

    for record in coverage:
        error_count_before = len(errors)
        record_id = record.get("id", "<missing>")
        atom_id = record.get("atom_id")
        atom = atom_by_id.get(atom_id)
        if not atom:
            errors.append(f"{record_id} references unknown atom {atom_id}")
            continue
        coverage_by_atom.setdefault(atom_id, []).append(record)
        rep_id = record.get("representative_type_id")
        if rep_id != atom.get("representative_type_id"):
            errors.append(f"{record_id} maps {atom_id} to a different representative")
        target_kind = record.get("target_kind")
        if target_kind not in SEMANTIC_TARGET_KINDS:
            errors.append(f"{record_id} has invalid target_kind")
        targets = record.get("target_component_ids")
        if not isinstance(targets, list) or not targets:
            errors.append(f"{record_id} has no target components")
            targets = []
        component_map = component_maps.get(rep_id, {})
        for target in targets:
            if component_map.get(target) != target_kind:
                errors.append(f"{record_id} targets unknown or mismatched component {target}")
        allowed = PROBLEM_TARGETS if atom.get("category") == "problem" else EXPLANATION_TARGETS
        if target_kind not in allowed:
            errors.append(f"{record_id} maps {atom.get('category')} atom to the wrong output side")
        if record.get("integration_mode") not in SEMANTIC_INTEGRATION_MODES:
            errors.append(f"{record_id} has invalid integration_mode")
        if record.get("status") != "covered":
            errors.append(f"{record_id} is not covered")
        if len(errors) > error_count_before:
            invalid_coverage_atoms.add(atom_id)

    for atom in atoms:
        if atom.get("relevance_status") != "required":
            continue
        atom_id = atom.get("id")
        mappings = coverage_by_atom.get(atom_id, [])
        if len(mappings) != 1:
            errors.append(f"{atom_id} has {len(mappings)} coverage records, expected 1")

    for group_id, atom_ids in duplicate_groups.items():
        required = [
            atom_id
            for atom_id in atom_ids
            if atom_by_id.get(atom_id, {}).get("relevance_status") == "required"
        ]
        if len(required) < 2:
            continue
        mappings = [coverage_by_atom.get(atom_id, []) for atom_id in required]
        if any(len(items) != 1 or items[0].get("integration_mode") != "duplicate_merged" for items in mappings):
            errors.append(f"duplicate group {group_id} is not explicitly merged")
            invalid_coverage_atoms.update(required)
        elif len({tuple(items[0].get("target_component_ids", [])) for items in mappings}) != 1:
            errors.append(f"duplicate group {group_id} does not share one output component")
            invalid_coverage_atoms.update(required)

    for group_id, atom_ids in conflict_groups.items():
        required = [
            atom_id
            for atom_id in atom_ids
            if atom_by_id.get(atom_id, {}).get("relevance_status") == "required"
        ]
        mappings = [coverage_by_atom.get(atom_id, []) for atom_id in required]
        if len(required) >= 2:
            if any(len(items) != 1 or items[0].get("integration_mode") != "conditional_split" for items in mappings):
                errors.append(f"conflict group {group_id} is unresolved or hidden")
                invalid_coverage_atoms.update(required)
            elif len({tuple(items[0].get("target_component_ids", [])) for items in mappings}) < 2:
                errors.append(f"conflict group {group_id} is not split into distinct output components")
                invalid_coverage_atoms.update(required)

    for review in reviews:
        reviews_by_rep.setdefault(review.get("representative_type_id"), []).append(review)

    for representative in representatives:
        rep_id = representative.get("id")
        problem_text = " ".join(
            str(component.get("text", ""))
            for component in representative.get("problem_components", [])
            if isinstance(component, dict)
        )
        if not substantive_text(problem_text):
            errors.append(f"{rep_id} representative problem has no substantive problem text")
        answer_components = representative.get("answer_components", [])
        explanation_components = representative.get("explanation_components", [])
        if not any(substantive_text(item.get("text")) for item in answer_components if isinstance(item, dict)):
            errors.append(f"{rep_id} representative solution has no substantive answer")
        if not any(substantive_text(item.get("text")) for item in explanation_components if isinstance(item, dict)):
            errors.append(f"{rep_id} representative solution has no substantive explanation")

        linked_question_ids = set(representative.get("question_ids", []))
        if len(linked_question_ids) > 1:
            solution_components = [*answer_components, *explanation_components]
            has_integrated_solution = any(
                linked_question_ids.issubset(set(source.get("source_question_ids", [])))
                for component in solution_components
                if isinstance(component, dict) and substantive_text(component.get("text"))
                for source in component.get("provenance", [])
                if source.get("kind") == "ai_reconstruction_from_questions"
            )
            if not has_integrated_solution:
                errors.append(
                    f"{rep_id} has no coherent synthesized solution spanning every linked question"
                )
        rep_atoms = [
            atom
            for atom in atoms
            if atom.get("representative_type_id") == rep_id and atom.get("relevance_status") == "required"
        ]
        for question_id in representative.get("question_ids", []):
            question = questions.get(question_id, {})
            required_source_parts: list[tuple[str, int | None]] = []
            if question.get("original_problem"):
                required_source_parts.append(("original_problem", None))
            required_source_parts.extend(
                ("original_choices", index)
                for index, choice in enumerate(question.get("original_choices", []))
                if choice
            )
            if question.get("original_answer"):
                required_source_parts.append(("original_answer", None))
            if question.get("original_explanation"):
                required_source_parts.append(("original_explanation", None))
            for source_field, choice_index in required_source_parts:
                matches = [
                    atom
                    for atom in rep_atoms
                    if atom.get("source_question_id") == question_id
                    and atom.get("source_field") == source_field
                    and (source_field != "original_choices" or atom.get("choice_index") == choice_index)
                ]
                if not matches:
                    suffix = f"[{choice_index}]" if choice_index is not None else ""
                    errors.append(f"{rep_id} has no required atom for {question_id}.{source_field}{suffix}")

    summaries: list[dict[str, Any]] = []
    for representative in representatives:
        rep_id = representative.get("id")
        rep_atoms = [atom for atom in atoms if atom.get("representative_type_id") == rep_id]
        required_problem = [a for a in rep_atoms if a.get("relevance_status") == "required" and a.get("category") == "problem"]
        required_explanation = [a for a in rep_atoms if a.get("relevance_status") == "required" and a.get("category") != "problem"]
        if not required_problem:
            errors.append(f"{rep_id} has no required problem atoms")
        if not required_explanation:
            errors.append(f"{rep_id} has no required explanation atoms")
        mapped_problem = sum(
            len(coverage_by_atom.get(a.get("id"), [])) == 1 and a.get("id") not in invalid_coverage_atoms
            for a in required_problem
        )
        mapped_explanation = sum(
            len(coverage_by_atom.get(a.get("id"), [])) == 1 and a.get("id") not in invalid_coverage_atoms
            for a in required_explanation
        )
        rep_reviews = reviews_by_rep.get(rep_id, [])
        unresolved = (
            sum(a.get("relevance_status") == "review_required" for a in rep_atoms)
            + len(required_problem) - mapped_problem
            + len(required_explanation) - mapped_explanation
        )
        if len(rep_reviews) != 1:
            errors.append(f"{rep_id} has {len(rep_reviews)} second-pass reviews, expected 1")
            unresolved += 1
        else:
            review = rep_reviews[0]
            if review.get("status") != "complete":
                errors.append(f"{rep_id} second-pass reread is not complete")
                unresolved += 1
            quality = review.get("synthesis_quality", {})
            required_quality = (
                "problem_complete",
                "explanation_complete",
                "coherent_single_problem",
                "coherent_single_answer",
                "format_complete",
            )
            failed_quality = [key for key in required_quality if quality.get(key) is not True]
            if failed_quality:
                errors.append(f"{rep_id} synthesis quality review failed: {failed_quality}")
                unresolved += len(failed_quality)
            unresolved_ids = review.get("unresolved_atom_ids")
            if not isinstance(unresolved_ids, list) or unresolved_ids:
                errors.append(f"{rep_id} second-pass reread has unresolved atoms")
                unresolved += len(unresolved_ids or [])
            discovered = review.get("discovered_atom_ids")
            if not isinstance(discovered, list) or any(
                atom_id not in atom_by_id or atom_by_id[atom_id].get("representative_type_id") != rep_id
                for atom_id in discovered
            ):
                errors.append(f"{rep_id} second-pass reread has invalid discovered atoms")
            reviewed_sources = review.get("reviewed_sources", [])
            if not isinstance(reviewed_sources, list):
                errors.append(f"{rep_id} second-pass reviewed_sources must be a list")
                reviewed_sources = []
            reviewed_pairs: set[tuple[Any, Any]] = set()
            for item in reviewed_sources:
                if not isinstance(item, dict) or not isinstance(item.get("pages"), list):
                    errors.append(f"{rep_id} second-pass reviewed source entry is invalid")
                    continue
                reviewed_pairs.update((item.get("source_artifact_id"), page) for page in item["pages"])
            required_pairs = {
                (questions[qid].get("source_artifact_id"), questions[qid].get("source_page"))
                for qid in representative.get("question_ids", [])
                if qid in questions
            }
            required_pairs.update(
                (atom.get("source_artifact_id"), atom.get("source_page"))
                for atom in rep_atoms
                if atom.get("relevance_status") in {"required", "review_required"}
                and atom.get("category") != "external_supplement"
            )
            missing_pairs = sorted(required_pairs - reviewed_pairs, key=lambda item: (str(item[0]), str(item[1])))
            if missing_pairs:
                errors.append(f"{rep_id} second-pass reread misses source pages: {missing_pairs}")
                unresolved += len(missing_pairs)

        summaries.append(
            {
                "representative_type_id": rep_id,
                "title": representative.get("title", ""),
                "lecture_unit": representative.get("lecture_unit", ""),
                "problem_required": len(required_problem),
                "problem_mapped": mapped_problem,
                "explanation_required": len(required_explanation),
                "explanation_mapped": mapped_explanation,
                "unresolved": unresolved,
                "status": "complete" if (
                    mapped_problem == len(required_problem)
                    and mapped_explanation == len(required_explanation)
                    and unresolved == 0
                    and len(rep_reviews) == 1
                    and rep_reviews[0].get("status") == "complete"
                ) else "review_required",
            }
        )
    return errors, summaries


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

    source_records = {record.get("id"): record for record in sources if record.get("id")}
    source_ids = set(source_records)
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
    component_maps: dict[str, dict[str, str]] = {}
    for representative in representatives:
        rep_id = representative.get("id", "<missing>")
        component_maps[rep_id] = representative_components(representative, rep_id, errors)
        linked_ids = representative.get("question_ids", [])
        for question_id in linked_ids:
            linked_counts[question_id] += 1
            if question_id not in questions:
                errors.append(f"{rep_id} references unknown question {question_id}")
        for key in ("problem_components", "choice_components", "answer_components", "explanation_components"):
            components = representative.get(key)
            if not isinstance(components, list):
                errors.append(f"{rep_id}.{key} must be a list")
                continue
            for index, component in enumerate(components):
                if not isinstance(component, dict):
                    errors.append(f"{rep_id}.{key}[{index}] must be an object")
                    continue
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
            if not representative.get("choice_components"):
                errors.append(f"{rep_id} has no objective choice components")

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

    semantic_errors, coverage_summaries = validate_semantic_completeness(
        ledger,
        representatives,
        questions,
        source_records,
        image_ids,
        component_maps,
    )
    errors.extend(semantic_errors)

    return {
        "valid": not errors,
        "status": "complete_candidate" if not errors else "review_required",
        "errors": errors,
        "warnings": warnings,
        "representative_coverage": coverage_summaries,
        "counts": {
            "source_artifacts": len(sources),
            "question_occurrences": len(occurrences),
            "images": len(images),
            "representative_types": len(representatives),
            "prior_year_sequence": len(ledger.get("prior_year_sequence", [])),
            "audit_findings": len(findings),
            "semantic_atoms": len(ledger.get("semantic_atoms", [])),
            "semantic_coverage": len(ledger.get("semantic_coverage", [])),
            "second_pass_reviews": len(ledger.get("second_pass_reviews", [])),
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
