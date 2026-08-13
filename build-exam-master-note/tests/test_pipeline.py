from __future__ import annotations

import json
import base64
import copy
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from build_docx import build_document  # noqa: E402
from build_manifest import approve_manifest, build_manifest, verify_approval  # noqa: E402
from normalize_sources import normalize, text_integrity_findings  # noqa: E402
from validate_ledger import validate_ledger  # noqa: E402
from verify_docx import read_parts, verify_docx, visible_text  # noqa: E402


def original(question_id: str, field: str, choice_index: int | None = None) -> list[dict]:
    source = {
        "kind": "original",
        "source_question_id": question_id,
        "source_field": field,
    }
    if choice_index is not None:
        source["choice_index"] = choice_index
    return [source]


def attach_semantic_contract(ledger: dict) -> dict:
    questions = {item["id"]: item for item in ledger.get("question_occurrences", [])}
    images = {item["id"]: item for item in ledger.get("images", [])}
    atoms: list[dict] = []
    mappings: list[dict] = []
    reviews: list[dict] = []

    for rep_index, representative in enumerate(ledger.get("representative_types", []), start=1):
        rep_id = representative["id"]
        component_index = 0
        atom_index = 0

        def register(component: dict, target_kind: str, category: str, atom_type: str) -> None:
            nonlocal component_index, atom_index
            component_index += 1
            atom_index += 1
            component["id"] = f"C-{rep_index}-{component_index}"
            provenance = component.get("provenance", [{}])[0]
            question_id = provenance.get("source_question_id")
            if not question_id:
                question_ids = provenance.get("source_question_ids", representative.get("question_ids", []))
                question_id = question_ids[0] if question_ids else None
            question = questions.get(question_id, {})
            source_id = provenance.get("source_artifact_id") or question.get("source_artifact_id")
            source_page = provenance.get("source_page") or question.get("source_page")
            source_field = provenance.get("source_field")
            source_text = component.get("text", "")
            if question and source_field == "original_choices":
                source_text = question["original_choices"][provenance["choice_index"]]
            elif question and source_field:
                source_text = question.get(source_field, source_text)
            elif question and category == "problem":
                source_text = question.get("original_problem", source_text)
            atom = {
                "id": f"A-{rep_index}-{atom_index}",
                "representative_type_id": rep_id,
                "category": category,
                "atom_type": atom_type,
                "source_artifact_id": source_id,
                "source_page": source_page,
                "text": source_text,
                "provenance_kind": provenance.get("kind", "source_unverified"),
                "relevance_status": "required",
                "status": "verified",
            }
            if category == "external_supplement":
                atom.pop("source_artifact_id", None)
                atom.pop("source_page", None)
                atom["citation"] = provenance.get("citation")
                atom["locator"] = provenance.get("locator")
            if category == "problem" and question_id:
                atom["source_question_id"] = question_id
                atom["source_field"] = source_field or "original_problem"
                if source_field == "original_choices":
                    atom["choice_index"] = provenance["choice_index"]
            if category == "original_explanation":
                atom["source_question_id"] = question_id
                atom["source_field"] = source_field or "original_explanation"
            atoms.append(atom)
            mappings.append(
                {
                    "id": f"M-{rep_index}-{atom_index}",
                    "atom_id": atom["id"],
                    "representative_type_id": rep_id,
                    "target_kind": target_kind,
                    "target_component_ids": [component["id"]],
                    "integration_mode": "exact" if provenance.get("kind") == "original" else "synthesized",
                    "status": "covered",
                }
            )

        for component in representative.get("problem_components", []):
            register(component, "problem_component", "problem", "stem")
        for component in representative.get("choice_components", []):
            register(component, "choice_component", "problem", "choice")
            for rationale in component.get("rationale_components", []):
                kind = rationale.get("provenance", [{}])[0].get("kind")
                category = "original_explanation" if kind == "original" else ("external_supplement" if kind == "external_ai_supplement" else "lecture_note")
                register(rationale, "rationale_component", category, "rationale")
        for component in representative.get("answer_components", []):
            kind = component.get("provenance", [{}])[0].get("kind")
            category = "original_explanation" if kind == "original" else ("external_supplement" if kind == "external_ai_supplement" else "lecture_note")
            register(component, "answer_component", category, "answer")
        for component in representative.get("explanation_components", []):
            kind = component.get("provenance", [{}])[0].get("kind")
            category = "original_explanation" if kind == "original" else ("external_supplement" if kind == "external_ai_supplement" else "lecture_note")
            register(component, "explanation_component", category, "explanation")

        represented_parts = {
            (item.get("source_question_id"), item.get("source_field"), item.get("choice_index"))
            for item in atoms
            if item["representative_type_id"] == rep_id
        }

        def add_source_atom(
            question_id: str,
            source_field: str,
            text: str,
            target_kind: str,
            target_component_id: str,
            choice_index: int | None = None,
        ) -> None:
            nonlocal atom_index
            key = (question_id, source_field, choice_index)
            if key in represented_parts or not text:
                return
            atom_index += 1
            question = questions[question_id]
            atom = {
                "id": f"A-{rep_index}-{atom_index}",
                "representative_type_id": rep_id,
                "category": "problem" if source_field in {"original_problem", "original_choices"} else "original_explanation",
                "atom_type": "choice" if source_field == "original_choices" else ("stem" if source_field == "original_problem" else "explanation"),
                "source_artifact_id": question["source_artifact_id"],
                "source_page": question["source_page"],
                "source_question_id": question_id,
                "source_field": source_field,
                "text": text,
                "provenance_kind": "original",
                "relevance_status": "required",
                "status": "verified",
            }
            if choice_index is not None:
                atom["choice_index"] = choice_index
            atoms.append(atom)
            mappings.append(
                {
                    "id": f"M-{rep_index}-{atom_index}",
                    "atom_id": atom["id"],
                    "representative_type_id": rep_id,
                    "target_kind": target_kind,
                    "target_component_ids": [target_component_id],
                    "integration_mode": "synthesized",
                    "status": "covered",
                }
            )
            represented_parts.add(key)

        problem_target = representative["problem_components"][0]["id"]
        answer_targets = representative.get("answer_components", [])
        explanation_targets = representative.get("explanation_components", [])
        fallback_answer_kind = "answer_component" if answer_targets else "explanation_component"
        fallback_answer_id = (answer_targets or explanation_targets)[0]["id"]
        for question_id in representative.get("question_ids", []):
            question = questions[question_id]
            add_source_atom(question_id, "original_problem", question["original_problem"], "problem_component", problem_target)
            for choice_index, choice in enumerate(question.get("original_choices", [])):
                target = next(
                    (item["id"] for item in representative.get("choice_components", []) if item.get("text") == choice),
                    problem_target,
                )
                kind = "choice_component" if target != problem_target else "problem_component"
                add_source_atom(question_id, "original_choices", choice, kind, target, choice_index)
            add_source_atom(
                question_id,
                "original_answer",
                question["original_answer"],
                fallback_answer_kind,
                fallback_answer_id,
            )
            explanation_target = next(
                (
                    item["id"]
                    for item in explanation_targets
                    if item.get("text") == question.get("original_explanation")
                ),
                fallback_answer_id,
            )
            explanation_kind = (
                "explanation_component"
                if any(item["id"] == explanation_target for item in explanation_targets)
                else fallback_answer_kind
            )
            add_source_atom(
                question_id,
                "original_explanation",
                question["original_explanation"],
                explanation_kind,
                explanation_target,
            )

        for question_id in representative.get("question_ids", []):
            for image_id in questions.get(question_id, {}).get("image_ids", []):
                image = images[image_id]
                atom_index += 1
                atom = {
                    "id": f"A-{rep_index}-{atom_index}",
                    "representative_type_id": rep_id,
                    "category": "problem",
                    "atom_type": "image",
                    "source_artifact_id": image["source_artifact_id"],
                    "source_page": image["source_page"],
                    "image_id": image_id,
                    "provenance_kind": "original",
                    "relevance_status": "required",
                    "status": "verified",
                }
                atoms.append(atom)
                mappings.append(
                    {
                        "id": f"M-{rep_index}-{atom_index}",
                        "atom_id": atom["id"],
                        "representative_type_id": rep_id,
                        "target_kind": "problem_component",
                        "target_component_ids": [representative["problem_components"][0]["id"]],
                        "integration_mode": "synthesized",
                        "status": "covered",
                    }
                )

        reviewed: dict[str, set[int]] = {}
        for question_id in representative.get("question_ids", []):
            question = questions[question_id]
            reviewed.setdefault(question["source_artifact_id"], set()).add(question["source_page"])
        for atom in [item for item in atoms if item["representative_type_id"] == rep_id]:
            if atom["category"] != "external_supplement":
                reviewed.setdefault(atom["source_artifact_id"], set()).add(atom["source_page"])
        reviews.append(
            {
                "id": f"P2-{rep_index}",
                "representative_type_id": rep_id,
                "reviewed_sources": [
                    {"source_artifact_id": source_id, "pages": sorted(pages)}
                    for source_id, pages in sorted(reviewed.items())
                ],
                "discovered_atom_ids": [],
                "unresolved_atom_ids": [],
                "notes": "정규화 원문을 독립적으로 재검토함",
                "status": "complete",
            }
        )

    ledger["schema_version"] = 2
    ledger["semantic_atoms"] = atoms
    ledger["semantic_coverage"] = mappings
    ledger["second_pass_reviews"] = reviews
    return ledger


def valid_ledger() -> dict:
    sources = [
        {
            "id": "S-1",
            "logical_artifact_id": "A-1",
            "file_name": "240901_0교시.pdf",
            "format": "pdf",
            "sha256": "a" * 64,
            "size_bytes": 100,
            "source_role": "current_lecture_past_paper",
            "source_link_index": 1,
            "page_count": 2,
            "processed_pages": [1, 2],
            "status": "normalized",
        },
        {
            "id": "S-2",
            "logical_artifact_id": "A-2",
            "file_name": "2024 3Q 기출 복기.pdf",
            "format": "pdf",
            "sha256": "b" * 64,
            "size_bytes": 100,
            "source_role": "reconstruction_order_source",
            "source_link_index": 2,
            "page_count": 1,
            "processed_pages": [1],
            "status": "normalized",
        },
    ]
    questions = [
        {
            "id": "Q-1",
            "source_artifact_id": "S-1",
            "year": 2021,
            "source_order": 1,
            "source_page": 2,
            "question_type": "객관식",
            "original_problem": "옳은 것을 고르시오.",
            "original_choices": ["A 선지", "B 선지"],
            "original_answer": "정답 A",
            "original_explanation": "A가 옳다.",
            "image_ids": [],
            "representative_type_id": "R-1",
            "word_location": "part1/R-1/Q-1",
            "status": "verified",
        },
        {
            "id": "Q-2",
            "source_artifact_id": "S-2",
            "year": 2024,
            "source_order": 1,
            "source_page": 1,
            "question_type": "객관식",
            "original_problem": "맞는 것?",
            "original_choices": ["B 선지", "C 선지"],
            "original_answer": "A라고 복기",
            "original_explanation": "해설 복기 불완전",
            "image_ids": [],
            "representative_type_id": "R-1",
            "word_location": "part1/R-1/Q-2;part2/1/Q-2",
            "status": "verified",
        },
    ]
    rationale = {
        "text": "강의 정리에서 확인한 선지별 근거",
        "provenance": [
            {
                "kind": "lecture_note_supplement",
                "source_artifact_id": "S-1",
                "source_page": 1,
            }
        ],
    }
    representative = {
        "id": "R-1",
        "title": "완성형 객관식",
        "question_type": "객관식",
        "lecture_unit": "제1강",
        "lecture_order": 1,
        "question_ids": ["Q-1", "Q-2"],
        "problem_components": [
            {
                "text": "옳은 설명을 모두 판별하시오.",
                "provenance": [
                    {
                        "kind": "ai_reconstruction_from_questions",
                        "source_question_ids": ["Q-1", "Q-2"],
                    }
                ],
            }
        ],
        "choice_components": [
            {"text": "A 선지", "provenance": original("Q-1", "original_choices", 0), "verdict": "O", "rationale_components": [copy.deepcopy(rationale)]},
            {"text": "B 선지", "provenance": original("Q-1", "original_choices", 1), "verdict": "X", "rationale_components": [copy.deepcopy(rationale)]},
            {"text": "C 선지", "provenance": original("Q-2", "original_choices", 1), "verdict": "X", "rationale_components": [copy.deepcopy(rationale)]},
        ],
        "answer_components": [
            {"text": "정답 A", "provenance": original("Q-1", "original_answer")},
        ],
        "explanation_components": [
            {"text": "A가 옳다.", "provenance": original("Q-1", "original_explanation")},
            {"text": "해설 복기 불완전", "provenance": original("Q-2", "original_explanation")},
            copy.deepcopy(rationale),
        ],
    }
    ledger = {
        "schema_version": 1,
        "manifest_fingerprint": "f" * 64,
        "approved_manifest_fingerprint": "f" * 64,
        "course_title": "가상 과목 3Q",
        "source_artifacts": sources,
        "question_occurrences": questions,
        "images": [],
        "representative_types": [representative],
        "prior_year_sequence": [
            {
                "sequence": 1,
                "question_ids": ["Q-2"],
                "reconstruction_source_ids": ["S-2"],
                "explanation_source_ids": ["S-2"],
                "conflict_status": "none",
                "supplement_components": [
                    {
                        "text": "대표유형의 완전 해설을 참고한다.",
                        "provenance": [
                            {"kind": "master_note_supplement", "representative_type_id": "R-1"}
                        ],
                    }
                ],
            }
        ],
        "audit_findings": [],
        "verification_counts": {"원문 문항": 2, "이미지": 0},
    }
    return attach_semantic_contract(ledger)


class ManifestTests(unittest.TestCase):
    def test_example_excludes_only_combined_file(self) -> None:
        current_names = [
            "(추족) 250922_RPD2_Lab Procedures_0교시.pdf",
            "2025 RPD2 중간고사 합본.pdf",
            "250825_RPD2_A_0교시.pdf",
            "250902_RPD2_B_0교시.pdf",
            "250908_RPD2_C_0교시.pdf",
            "250915_RPD2_D_1교시.pdf",
            "250915_RPD2_E_0교시.pdf",
            "250922_RPD2_F_1교시.pdf",
            "250929_RPD2_G_0교시.pdf",
        ]
        inventory = {
            "first_link": "https://onedrive.live.com/path/2025/3Q",
            "second_link": "https://onedrive.live.com/path/exams",
            "exam_scope": "3Q",
            "first_link_items": [
                {"name": name, "relative_path": name, "first_page_text": name}
                for name in current_names
            ],
            "second_link_items": [
                {"name": "2024 3Q 기출 복기.pdf", "relative_path": "2024 3Q 기출 복기.pdf"},
                {"name": "2024 3Q 기출 복기.hwpx", "relative_path": "2024 3Q 기출 복기.hwpx"},
                {"name": "2023 3Q 해설.pdf", "relative_path": "2023 3Q 해설.pdf"},
            ],
        }
        manifest = build_manifest(inventory)
        first_included = [item for item in manifest["included_files"] if item["link_index"] == 1]
        self.assertEqual(8, len(first_included))
        self.assertEqual(1, len([item for item in manifest["excluded_files"] if item["reason"] == "contains_합본"]))
        same_day = [item for item in first_included if item["lecture_date"] == "2025-09-15"]
        self.assertEqual([0, 1], [item["period"] for item in same_day])
        approved = approve_manifest(manifest)
        self.assertTrue(verify_approval(approved))
        approved["included_files"][0]["name"] = "tampered.pdf"
        self.assertFalse(verify_approval(approved))
        prior_groups = [group for group in manifest["logical_artifacts"] if group["link_index"] == 2]
        self.assertEqual(1, len(prior_groups))
        self.assertEqual(2, len(prior_groups[0]["file_ids"]))

    def test_rejects_non_direct_child(self) -> None:
        inventory = {
            "first_link": "https://onedrive.live.com/path/2025/3Q",
            "second_link": "https://onedrive.live.com/path/exams",
            "first_link_items": [{"name": "a.pdf", "relative_path": "parent/a.pdf"}],
            "second_link_items": [],
        }
        manifest = build_manifest(inventory)
        self.assertEqual("OUTSIDE_DIRECT_LINK_SCOPE", manifest["audit_findings"][0]["code"])


class LedgerTests(unittest.TestCase):
    def test_valid_ledger(self) -> None:
        report = validate_ledger(valid_ledger())
        self.assertTrue(report["valid"], report["errors"])

    def test_changed_original_is_rejected(self) -> None:
        ledger = valid_ledger()
        ledger["representative_types"][0]["choice_components"][0]["text"] = "A 선지 교정"
        report = validate_ledger(ledger)
        self.assertFalse(report["valid"])
        self.assertTrue(any("labeled original" in error for error in report["errors"]))

    def test_missing_repeated_choice_is_rejected(self) -> None:
        ledger = valid_ledger()
        ledger["representative_types"][0]["choice_components"].pop()
        report = validate_ledger(ledger)
        self.assertFalse(report["valid"])
        self.assertTrue(any("unknown or mismatched component" in error for error in report["errors"]))

    def test_unmapped_problem_atom_is_rejected(self) -> None:
        ledger = valid_ledger()
        atom = next(item for item in ledger["semantic_atoms"] if item["category"] == "problem")
        ledger["semantic_coverage"] = [
            item for item in ledger["semantic_coverage"] if item["atom_id"] != atom["id"]
        ]
        report = validate_ledger(ledger)
        self.assertFalse(report["valid"])
        self.assertTrue(any(f"{atom['id']} has 0 coverage" in error for error in report["errors"]))

    def test_missing_source_choice_atom_is_rejected(self) -> None:
        ledger = valid_ledger()
        atom = next(
            item
            for item in ledger["semantic_atoms"]
            if item.get("source_question_id") == "Q-2"
            and item.get("source_field") == "original_choices"
            and item.get("choice_index") == 0
        )
        ledger["semantic_atoms"] = [item for item in ledger["semantic_atoms"] if item["id"] != atom["id"]]
        ledger["semantic_coverage"] = [
            item for item in ledger["semantic_coverage"] if item["atom_id"] != atom["id"]
        ]
        report = validate_ledger(ledger)
        self.assertFalse(report["valid"])
        self.assertTrue(any("Q-2.original_choices[0]" in error for error in report["errors"]))

    def test_unmapped_explanation_and_lecture_atoms_are_rejected(self) -> None:
        for category in ("original_explanation", "lecture_note"):
            ledger = valid_ledger()
            atom = next(item for item in ledger["semantic_atoms"] if item["category"] == category)
            ledger["semantic_coverage"] = [
                item for item in ledger["semantic_coverage"] if item["atom_id"] != atom["id"]
            ]
            report = validate_ledger(ledger)
            self.assertFalse(report["valid"])
            self.assertTrue(any(f"{atom['id']} has 0 coverage" in error for error in report["errors"]))

    def test_second_pass_and_ambiguous_relevance_are_blocking(self) -> None:
        ledger = valid_ledger()
        ledger["second_pass_reviews"][0]["reviewed_sources"][0]["pages"] = []
        ledger["semantic_atoms"][0]["relevance_status"] = "review_required"
        report = validate_ledger(ledger)
        self.assertFalse(report["valid"])
        self.assertTrue(any("ambiguous relevance" in error for error in report["errors"]))
        self.assertTrue(any("second-pass reread misses source pages" in error for error in report["errors"]))

    def test_duplicate_atoms_can_share_one_synthesized_component(self) -> None:
        ledger = valid_ledger()
        atoms = [item for item in ledger["semantic_atoms"] if item["category"] == "lecture_note"][:2]
        self.assertEqual(2, len(atoms))
        mappings = {
            item["atom_id"]: item for item in ledger["semantic_coverage"] if item["atom_id"] in {a["id"] for a in atoms}
        }
        target = mappings[atoms[0]["id"]]["target_component_ids"]
        for atom in atoms:
            atom["duplicate_group_id"] = "DUP-1"
            mappings[atom["id"]]["target_component_ids"] = target
            mappings[atom["id"]]["target_kind"] = mappings[atoms[0]["id"]]["target_kind"]
            mappings[atom["id"]]["integration_mode"] = "duplicate_merged"
        report = validate_ledger(ledger)
        self.assertTrue(report["valid"], report["errors"])

    def test_conflicting_conditions_must_remain_split(self) -> None:
        ledger = valid_ledger()
        atoms = [item for item in ledger["semantic_atoms"] if item["category"] == "problem"][:2]
        mappings = {
            item["atom_id"]: item for item in ledger["semantic_coverage"] if item["atom_id"] in {a["id"] for a in atoms}
        }
        for atom in atoms:
            atom["conflict_group_id"] = "CONFLICT-1"
            mappings[atom["id"]]["integration_mode"] = "conditional_split"
        self.assertTrue(validate_ledger(ledger)["valid"])
        mappings[atoms[1]["id"]]["target_component_ids"] = mappings[atoms[0]["id"]]["target_component_ids"]
        mappings[atoms[1]["id"]]["target_kind"] = mappings[atoms[0]["id"]]["target_kind"]
        report = validate_ledger(ledger)
        self.assertFalse(report["valid"])
        self.assertTrue(any("not split" in error for error in report["errors"]))

    def test_external_supplement_requires_authoritative_locator(self) -> None:
        ledger = valid_ledger()
        ledger["representative_types"][0]["explanation_components"].append(
            {
                "text": "족보에 없는 필수 공백만 외부 근거로 보충",
                "provenance": [
                    {
                        "kind": "external_ai_supplement",
                        "citation": "공식 학회 지침",
                        "locator": "https://example.org/guideline",
                    }
                ],
            }
        )
        attach_semantic_contract(ledger)
        self.assertTrue(validate_ledger(ledger)["valid"])
        external = next(item for item in ledger["semantic_atoms"] if item["category"] == "external_supplement")
        external.pop("locator")
        report = validate_ledger(ledger)
        self.assertFalse(report["valid"])
        self.assertTrue(any("external atom lacks" in error for error in report["errors"]))


class NormalizationTests(unittest.TestCase):
    def test_pdf_and_hwpx_normalization(self) -> None:
        from pypdf import PdfWriter

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "sample.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)
            with pdf_path.open("wb") as handle:
                writer.write(handle)
            pdf_report = normalize(pdf_path, root / "pdf-out", False)
            self.assertEqual("normalized", pdf_report["status"])
            self.assertEqual(1, pdf_report["page_count"])

            hwpx_path = root / "sample.hwpx"
            with zipfile.ZipFile(hwpx_path, "w") as archive:
                archive.writestr(
                    "Contents/section0.xml",
                    '<root xmlns:hp="urn:test"><hp:t>한글 원문</hp:t></root>',
                )
                archive.writestr("BinData/image.png", b"not-a-real-image")
            hwpx_report = normalize(hwpx_path, root / "hwpx-out", False)
            self.assertEqual("review_required", hwpx_report["status"])
            self.assertEqual("한글 원문", hwpx_report["pages"][0]["text"])
            self.assertEqual(1, len(hwpx_report["unmapped_images"]))
            self.assertEqual("HWPX_PAGE_LAYOUT_UNVERIFIED", hwpx_report["audit_findings"][0]["code"])

    def test_encoding_corruption_is_blocking(self) -> None:
        findings = text_integrity_findings("���� 깨짐", "broken.txt")
        self.assertEqual("TEXT_ENCODING_CORRUPTION", findings[0]["code"])


class DocxTests(unittest.TestCase):
    @staticmethod
    def save_and_verify(ledger: dict, root: Path, name: str = "master-note.docx") -> tuple[Path, dict]:
        output = root / name
        document = build_document(ledger, None, "완성 후보")
        document.save(output)
        return output, verify_docx(output, ledger)

    def test_build_and_independently_verify(self) -> None:
        ledger = valid_ledger()
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "question-image.png"
            image_path.write_bytes(
                base64.b64decode(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
                )
            )
            ledger["images"] = [
                {
                    "id": "IMG-1",
                    "source_artifact_id": "S-1",
                    "source_page": 2,
                    "path": str(image_path),
                    "question_ids": ["Q-1"],
                    "provenance": [{"kind": "original", "source_image_id": "IMG-1"}],
                    "word_location": "part1/R-1/Q-1/IMG-1",
                    "status": "verified",
                }
            ]
            ledger["question_occurrences"][0]["image_ids"] = ["IMG-1"]
            attach_semantic_contract(ledger)
            output, report = self.save_and_verify(ledger, Path(tmp))
            self.assertTrue(report["valid"], report["errors"])
            self.assertGreaterEqual(report["counts"]["drawings_found"], 1)

    def test_a4_45_55_repeated_headers_and_header_only(self) -> None:
        ledger = valid_ledger()
        with tempfile.TemporaryDirectory() as tmp:
            output, report = self.save_and_verify(ledger, Path(tmp), "layout.docx")
            self.assertTrue(report["valid"], report["errors"])
            self.assertEqual(4, report["counts"]["problem_tables_found"])
            with zipfile.ZipFile(output) as archive:
                document_xml = archive.read("word/document.xml").decode("utf-8")
                footer_xml = "".join(
                    archive.read(name).decode("utf-8")
                    for name in archive.namelist()
                    if name.startswith("word/footer") and name.endswith(".xml")
                )
                header_xml = "".join(
                    archive.read(name).decode("utf-8")
                    for name in archive.namelist()
                    if name.startswith("word/header") and name.endswith(".xml")
                )
            self.assertIn('w:w="11906"', document_xml)
            self.assertIn('w:h="16838"', document_xml)
            self.assertIn('w:tblCaption w:val="representative:R-1"', document_xml)
            self.assertIn('w:w="4428"', document_xml)
            self.assertIn('w:w="5412"', document_xml)
            self.assertIn("w:tblHeader", document_xml)
            self.assertIn("제1강", header_xml)
            self.assertIn("작년 기출 실전 순서", header_xml)
            self.assertNotIn("Page", footer_xml)
            self.assertNotIn("PAGE", footer_xml)
            document_root, _ = read_parts(output)
            learner_text = visible_text(document_root)
            self.assertNotIn("Q-1", learner_text)
            self.assertNotIn("R-1", learner_text)
            self.assertNotIn("IMG-1", learner_text)
            self.assertIn("[원문 · 240901_0교시.pdf · 2쪽]", learner_text)
            self.assertIn("[기출 통합 재구성 · 2021년·2024년 기출 참고]", learner_text)
            self.assertIn("문제 완전성", learner_text)
            self.assertIn("해설 완전성", learner_text)
            self.assertIn("완성형 객관식", learner_text)
            self.assertNotIn("심각도", learner_text)
            self.assertNotIn("코드", learner_text)

    def test_generated_ids_are_hidden_but_source_literals_are_preserved(self) -> None:
        ledger = valid_ledger()
        ledger["question_occurrences"][0]["original_problem"] = "Q-1 표지를 포함한 원문"
        attach_semantic_contract(ledger)
        with tempfile.TemporaryDirectory() as tmp:
            _, report = self.save_and_verify(ledger, Path(tmp), "source-id-literal.docx")
            self.assertTrue(report["valid"], report["errors"])

        ledger = valid_ledger()
        ledger["representative_types"][0]["title"] = "완성형 객관식 R-1"
        with tempfile.TemporaryDirectory() as tmp:
            _, report = self.save_and_verify(ledger, Path(tmp), "leaked-id.docx")
            self.assertFalse(report["valid"])
            self.assertTrue(any("technical ID is visible" in error for error in report["errors"]))

    def test_compact_audit_expands_only_for_review_cases(self) -> None:
        ledger = valid_ledger()
        atom = next(item for item in ledger["semantic_atoms"] if item["category"] == "problem")
        ledger["semantic_coverage"] = [
            item for item in ledger["semantic_coverage"] if item["atom_id"] != atom["id"]
        ]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "review.docx"
            build_document(ledger, None, "검수 필요 초안").save(output)
            root, _ = read_parts(output)
            text = visible_text(root)
            self.assertIn("검수 필요 사항", text)
            self.assertIn("문제 의미 반영", text)
            self.assertNotIn(atom["id"], text)

    def test_types_repetition_long_explanation_and_conflict(self) -> None:
        ledger = valid_ledger()
        repeated = copy.deepcopy(ledger["question_occurrences"][0])
        repeated.update({"id": "Q-3", "year": 2022, "source_order": 2, "word_location": "part1/R-1/Q-3"})
        ledger["question_occurrences"].append(repeated)
        ledger["representative_types"][0]["question_ids"].append("Q-3")
        ledger["representative_types"][0]["explanation_components"].append(
            {
                "text": "상세 기전과 예외를 빠짐없이 설명한다. " * 80,
                "provenance": [
                    {"kind": "lecture_note_supplement", "source_artifact_id": "S-1", "source_page": 1}
                ],
            }
        )

        essay = {
            "id": "Q-4",
            "source_artifact_id": "S-1",
            "year": 2023,
            "source_order": 3,
            "source_page": 2,
            "question_type": "서술형",
            "original_problem": "진단과 치료를 모두 서술하시오.",
            "original_choices": [],
            "original_answer": "진단 기준과 치료 원칙",
            "original_explanation": "서술형 원문 해설",
            "image_ids": [],
            "representative_type_id": "R-2",
            "word_location": "part1/R-2/Q-4",
            "status": "verified",
        }
        short = {
            "id": "Q-5",
            "source_artifact_id": "S-1",
            "year": 2023,
            "source_order": 4,
            "source_page": 2,
            "question_type": "단답형",
            "original_problem": "진단명은?",
            "original_choices": [],
            "original_answer": "가상 진단",
            "original_explanation": "단답형 원문 해설",
            "image_ids": [],
            "representative_type_id": "R-3",
            "word_location": "part1/R-3/Q-5",
            "status": "verified",
        }
        ledger["question_occurrences"].extend([essay, short])
        ledger["representative_types"].extend(
            [
                {
                    "id": "R-2",
                    "title": "완성형 서술형",
                    "question_type": "서술형",
                    "lecture_unit": "제2강",
                    "lecture_order": 2,
                    "question_ids": ["Q-4"],
                    "problem_components": [{"text": essay["original_problem"], "provenance": original("Q-4", "original_problem")}],
                    "choice_components": [],
                    "answer_components": [
                        {
                            "text": "모든 하위 질문의 완전 답안",
                            "provenance": [
                                {"kind": "ai_reconstruction_from_questions", "source_question_ids": ["Q-4"]}
                            ],
                        }
                    ],
                    "explanation_components": [{"text": essay["original_explanation"], "provenance": original("Q-4", "original_explanation")}],
                },
                {
                    "id": "R-3",
                    "title": "완성형 단답형",
                    "question_type": "단답형",
                    "lecture_unit": "제3강",
                    "lecture_order": 3,
                    "question_ids": ["Q-5"],
                    "problem_components": [{"text": short["original_problem"], "provenance": original("Q-5", "original_problem")}],
                    "choice_components": [],
                    "answer_components": [{"text": short["original_answer"], "provenance": original("Q-5", "original_answer")}],
                    "explanation_components": [{"text": short["original_explanation"], "provenance": original("Q-5", "original_explanation")}],
                },
            ]
        )
        ledger["prior_year_sequence"][0]["conflict_status"] = "disputed"
        attach_semantic_contract(ledger)
        with tempfile.TemporaryDirectory() as tmp:
            output, report = self.save_and_verify(ledger, Path(tmp), "types.docx")
            self.assertTrue(report["valid"], report["errors"])
            with zipfile.ZipFile(output) as archive:
                xml = archive.read("word/document.xml").decode("utf-8")
            self.assertIn("원문 답과 보충 판정 불일치", xml)
            self.assertIn("모든 하위 질문의 완전 답안", xml)
            self.assertIn("가상 진단", xml)
            self.assertIn('w:tblCaption w:val="occurrence:part1:R-1:Q-3"', xml)
            representative_start = xml.index('w:tblCaption w:val="representative:R-1"')
            representative_end = xml.index("</w:tbl>", representative_start)
            self.assertNotIn("w:cantSplit", xml[representative_start:representative_end])


if __name__ == "__main__":
    unittest.main()
