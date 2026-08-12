#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from common import load_json
from validate_ledger import validate_ledger


def require_docx() -> None:
    try:
        import docx  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("python-docx is required to build the master note") from exc


def set_run_font(run: Any, name: str = "Malgun Gothic", size: float | None = None, **kwargs: Any) -> None:
    from docx.oxml.ns import qn
    from docx.shared import Pt

    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    for key, value in kwargs.items():
        setattr(run.font, key, value)


def set_cell_shading(cell: Any, fill: str) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), fill)


def set_table_geometry(table: Any, widths_dxa: list[int], indent_dxa: int = 120) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    if sum(widths_dxa) != 9360:
        raise ValueError("table widths must sum to 9360 DXA")
    table.autofit = False
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:type"), "dxa")
    tbl_w.set(qn("w:w"), "9360")
    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:type"), "dxa")
    tbl_ind.set(qn("w:w"), str(indent_dxa))

    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths_dxa:
        grid_col = OxmlElement("w:gridCol")
        grid_col.set(qn("w:w"), str(width))
        grid.append(grid_col)
    for row in table.rows:
        for index, cell in enumerate(row.cells):
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:type"), "dxa")
            tc_w.set(qn("w:w"), str(widths_dxa[index]))


def configure_styles(document: Any) -> None:
    from docx.enum.section import WD_SECTION
    from docx.enum.text import WD_LINE_SPACING
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt, RGBColor

    section = document.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    tokens = {
        "Normal": (11, "000000", 0, 6, 1.25),
        "Heading 1": (16, "2E74B5", 18, 10, 1.0),
        "Heading 2": (13, "2E74B5", 14, 7, 1.0),
        "Heading 3": (12, "1F4D78", 10, 5, 1.0),
    }
    for name, (size, color, before, after, spacing) in tokens.items():
        style = document.styles[name]
        style.font.name = "Malgun Gothic"
        style._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), "Malgun Gothic")
        style._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), "Malgun Gothic")
        style._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Malgun Gothic")
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.line_spacing = spacing

    header = section.header.paragraphs[0]
    header.text = "시험 단권화 노트"
    header.alignment = 0
    for run in header.runs:
        set_run_font(run, size=9)
        run.font.color.rgb = RGBColor.from_string("667085")

    footer = section.footer.paragraphs[0]
    footer.alignment = 2
    label = footer.add_run("Page ")
    set_run_font(label, size=9)
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)


def create_template(path: Path) -> None:
    require_docx()
    from docx import Document

    document = Document()
    configure_styles(document)
    document.save(path)


def provenance_label(
    provenance: list[dict[str, Any]],
    questions: dict[str, dict[str, Any]],
    sources: dict[str, dict[str, Any]],
) -> str:
    labels: list[str] = []
    for source in provenance:
        kind = source.get("kind")
        if kind == "original":
            question = questions.get(source.get("source_question_id"), {})
            artifact = sources.get(question.get("source_artifact_id"), {})
            labels.append(
                f"[원문 · {artifact.get('file_name', '?')} · p.{question.get('source_page', '?')} · {question.get('id', '?')}]"
            )
        elif kind == "ai_reconstruction_from_questions":
            labels.append(
                "[AI 복원 · 기출 근거 " + ",".join(source.get("source_question_ids", [])) + "]"
            )
        elif kind == "lecture_note_supplement":
            artifact = sources.get(source.get("source_artifact_id"), {})
            labels.append(
                f"[족보 보충 · {artifact.get('file_name', '?')} · p.{source.get('source_page', '?')}]"
            )
        elif kind == "master_note_supplement":
            labels.append(f"[단권화 보충 · {source.get('representative_type_id', '?')}]")
        elif kind == "external_ai_supplement":
            labels.append(
                f"[AI 외부 보충 · {source.get('citation', '?')} · {source.get('locator', '?')}]"
            )
        else:
            labels.append("[출처 확인 필요]")
    return " ".join(dict.fromkeys(labels))


def add_component(
    document: Any,
    component: dict[str, Any],
    questions: dict[str, dict[str, Any]],
    sources: dict[str, dict[str, Any]],
    prefix: str = "",
) -> None:
    from docx.shared import Pt, RGBColor

    paragraph = document.add_paragraph()
    paragraph.paragraph_format.keep_together = True
    if prefix:
        lead = paragraph.add_run(prefix)
        set_run_font(lead, size=11, bold=True)
    run = paragraph.add_run(component.get("text", ""))
    set_run_font(run, size=11)
    label_text = provenance_label(component.get("provenance", []), questions, sources)
    label = paragraph.add_run(f"\n{label_text}")
    set_run_font(label, size=8.5, italic=True)
    label.font.color.rgb = RGBColor.from_string("667085")
    paragraph.paragraph_format.space_after = Pt(6)


def add_image(document: Any, image: dict[str, Any], sources: dict[str, dict[str, Any]]) -> None:
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, RGBColor

    path = Path(image.get("path", ""))
    if not path.exists():
        paragraph = document.add_paragraph(f"[이미지 파일 없음 · {image.get('id', '?')}]")
        return
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    run.add_picture(str(path), width=Inches(5.8))
    artifact = sources.get(image.get("source_artifact_id"), {})
    caption = document.add_paragraph()
    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap_run = caption.add_run(
        f"{image.get('id')} · {artifact.get('file_name', '?')} · p.{image.get('source_page', '?')}"
    )
    set_run_font(cap_run, size=8.5, italic=True)
    cap_run.font.color.rgb = RGBColor.from_string("667085")


def add_title_page(document: Any, ledger: dict[str, Any], status: str) -> None:
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, RGBColor

    spacer = document.add_paragraph()
    spacer.paragraph_format.space_after = Pt(72)
    kicker = document.add_paragraph()
    kicker.alignment = WD_ALIGN_PARAGRAPH.CENTER
    kicker_run = kicker.add_run("VERIFIED EXAM REFERENCE")
    set_run_font(kicker_run, size=10, bold=True)
    kicker_run.font.color.rgb = RGBColor.from_string("2E74B5")
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title.add_run(ledger.get("course_title", "시험 단권화 노트"))
    set_run_font(title_run, size=28, bold=True)
    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle_run = subtitle.add_run(
        f"강의 순서 단권화 · 작년 기출 실전 순서 · 완전성 감사표\n상태: {status}"
    )
    set_run_font(subtitle_run, size=12)
    subtitle_run.font.color.rgb = RGBColor.from_string("475467")
    document.add_page_break()


def add_source_occurrence(
    document: Any,
    question: dict[str, Any],
    sources: dict[str, dict[str, Any]],
    images: dict[str, dict[str, Any]],
) -> None:
    artifact = sources.get(question.get("source_artifact_id"), {})
    document.add_heading(
        f"{question.get('year', '?')} · {question.get('id')} · {artifact.get('file_name', '?')} p.{question.get('source_page', '?')}",
        level=3,
    )
    fields = [
        ("문제", question.get("original_problem", ""), "original_problem"),
    ]
    fields.extend(
        (f"선지 {index}", choice, "original_choices")
        for index, choice in enumerate(question.get("original_choices", []), start=1)
    )
    fields.extend(
        [
            ("기존 답", question.get("original_answer", ""), "original_answer"),
            ("기존 해설", question.get("original_explanation", ""), "original_explanation"),
        ]
    )
    for label, text, field in fields:
        if text == "":
            continue
        paragraph = document.add_paragraph()
        label_run = paragraph.add_run(f"{label}: ")
        set_run_font(label_run, bold=True)
        text_run = paragraph.add_run(text)
        set_run_font(text_run)
        source_label = paragraph.add_run(
            f"\n[원문 · {artifact.get('file_name', '?')} · p.{question.get('source_page', '?')} · {question.get('id')}]"
        )
        set_run_font(source_label, size=8.5, italic=True)
    for image_id in question.get("image_ids", []):
        image = images.get(image_id)
        if image:
            add_image(document, image, sources)


def build_document(ledger: dict[str, Any], template: Path | None, status: str) -> Any:
    require_docx()
    from docx import Document

    document = Document(str(template)) if template and template.exists() else Document()
    configure_styles(document)
    add_title_page(document, ledger, status)

    sources = {item["id"]: item for item in ledger.get("source_artifacts", [])}
    questions = {item["id"]: item for item in ledger.get("question_occurrences", [])}
    images = {item["id"]: item for item in ledger.get("images", [])}

    document.add_heading("제1부. 강의 순서 단권화", level=1)
    for representative in ledger.get("representative_types", []):
        document.add_heading(
            f"{representative.get('lecture_unit', '미분류')} · {representative.get('title', '')} ({representative.get('id')})",
            level=2,
        )
        document.add_heading("대표 문제", level=3)
        for component in representative.get("problem_components", []):
            add_component(document, component, questions, sources)
        for index, component in enumerate(representative.get("choice_components", []), start=1):
            add_component(document, component, questions, sources, prefix=f"{index}. ")
            for rationale in component.get("rationale_components", []):
                add_component(
                    document,
                    rationale,
                    questions,
                    sources,
                    prefix=f"판정 {component.get('verdict', '?')}: ",
                )
        document.add_heading("완전 해설", level=3)
        for component in representative.get("explanation_components", []):
            add_component(document, component, questions, sources)
        document.add_heading("연도별 원문", level=3)
        linked = [questions[qid] for qid in representative.get("question_ids", []) if qid in questions]
        linked.sort(key=lambda item: (item.get("year") or 9999, item.get("source_order") or 9999))
        for question in linked:
            add_source_occurrence(document, question, sources, images)

    document.add_page_break()
    document.add_heading("제2부. 작년 기출 실전 순서", level=1)
    for entry in ledger.get("prior_year_sequence", []):
        document.add_heading(f"{entry.get('sequence')}번", level=2)
        for question_id in entry.get("question_ids", []):
            if question_id in questions:
                add_source_occurrence(document, questions[question_id], sources, images)
        if entry.get("conflict_status") not in {None, "none", "resolved"}:
            paragraph = document.add_paragraph(f"[원문 간 불일치 · {entry.get('conflict_status')}]")
            paragraph.style = document.styles["Normal"]
        for component in entry.get("supplement_components", []):
            add_component(document, component, questions, sources, prefix="보충: ")

    document.add_page_break()
    document.add_heading("제3부. 완전성 감사표", level=1)
    counts = ledger.get("verification_counts", {})
    document.add_paragraph(
        " · ".join(f"{key}: {value}" for key, value in counts.items())
        or "검증 수치는 독립 검증 보고서에서 채워집니다."
    )
    findings = ledger.get("audit_findings", [])
    table = document.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    headers = ["심각도", "코드", "내용", "원본 위치"]
    for index, header in enumerate(headers):
        table.rows[0].cells[index].text = header
        set_cell_shading(table.rows[0].cells[index], "E8EEF5")
    for finding in findings:
        cells = table.add_row().cells
        values = [
            finding.get("severity", ""),
            finding.get("code", ""),
            finding.get("message", ""),
            ", ".join(map(str, finding.get("source_locations", []))),
        ]
        for index, value in enumerate(values):
            cells[index].text = str(value)
    set_table_geometry(table, [1200, 1800, 4560, 1800])
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a three-part, provenance-aware exam DOCX")
    parser.add_argument("ledger", nargs="?")
    parser.add_argument("--template")
    parser.add_argument("--out")
    parser.add_argument("--review-draft", action="store_true")
    parser.add_argument("--create-template")
    args = parser.parse_args()
    if args.create_template:
        create_template(Path(args.create_template))
        return 0
    if not args.ledger or not args.out:
        parser.error("ledger and --out are required unless --create-template is used")
    ledger = load_json(args.ledger)
    validation = validate_ledger(ledger)
    if not validation["valid"] and not args.review_draft:
        print("ledger validation failed; use --review-draft only for an explicitly labeled draft")
        return 2
    status = "완성 후보" if validation["valid"] else "검수 필요 초안"
    document = build_document(ledger, Path(args.template) if args.template else None, status)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    document.save(output)
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
