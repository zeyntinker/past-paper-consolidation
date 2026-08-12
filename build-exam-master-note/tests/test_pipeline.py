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
from verify_docx import verify_docx  # noqa: E402


def original(question_id: str, field: str, choice_index: int | None = None) -> list[dict]:
    source = {
        "kind": "original",
        "source_question_id": question_id,
        "source_field": field,
    }
    if choice_index is not None:
        source["choice_index"] = choice_index
    return [source]


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
            {"text": "A 선지", "provenance": original("Q-1", "original_choices", 0), "verdict": "O", "rationale_components": [rationale]},
            {"text": "B 선지", "provenance": original("Q-1", "original_choices", 1), "verdict": "X", "rationale_components": [rationale]},
            {"text": "C 선지", "provenance": original("Q-2", "original_choices", 1), "verdict": "X", "rationale_components": [rationale]},
        ],
        "explanation_components": [
            {"text": "A가 옳다.", "provenance": original("Q-1", "original_explanation")},
            {"text": "해설 복기 불완전", "provenance": original("Q-2", "original_explanation")},
            rationale,
        ],
    }
    return {
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
        self.assertTrue(any("omits original objective choices" in error for error in report["errors"]))


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
                    "answer_components": [{"text": "모든 하위 질문의 완전 답안", "provenance": original("Q-4", "original_answer")}],
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
