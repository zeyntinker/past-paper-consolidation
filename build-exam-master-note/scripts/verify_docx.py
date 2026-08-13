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
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
NS = {"w": W_NS, "a": A_NS, "r": R_NS, "wp": WP_NS}


def attr(name: str) -> str:
    return f"{{{W_NS}}}{name}"


def visible_text(root: ElementTree.Element) -> str:
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
    return "".join(chunks)


def read_parts(docx_path: Path) -> tuple[ElementTree.Element, dict[str, ElementTree.Element]]:
    with zipfile.ZipFile(docx_path) as archive:
        document = ElementTree.fromstring(archive.read("word/document.xml"))
        parts: dict[str, ElementTree.Element] = {}
        for name in archive.namelist():
            if name.startswith("word/header") and name.endswith(".xml"):
                parts[name] = ElementTree.fromstring(archive.read(name))
            elif name.startswith("word/footer") and name.endswith(".xml"):
                parts[name] = ElementTree.fromstring(archive.read(name))
    return document, parts


def table_caption(table: ElementTree.Element) -> str:
    node = table.find("./w:tblPr/w:tblCaption", NS)
    return node.get(attr("val"), "") if node is not None else ""


def table_grid(table: ElementTree.Element) -> list[int]:
    return [int(node.get(attr("w"), "0")) for node in table.findall("./w:tblGrid/w:gridCol", NS)]


def inspect_layout(root: ElementTree.Element, parts: dict[str, ElementTree.Element]) -> dict[str, Any]:
    tables = root.findall(".//w:tbl", NS)
    identified = {table_caption(table): table for table in tables if table_caption(table)}
    headers = [visible_text(part).strip() for name, part in parts.items() if "/header" in name]
    footers = [visible_text(part).strip() for name, part in parts.items() if "/footer" in name]
    image_cell_spans: list[int] = []
    for table in tables:
        for cell in table.findall(".//w:tc", NS):
            if cell.find(".//a:blip", NS) is None:
                continue
            span_node = cell.find("./w:tcPr/w:gridSpan", NS)
            image_cell_spans.append(int(span_node.get(attr("val"), "1")) if span_node is not None else 1)
    return {
        "tables": tables,
        "identified_tables": identified,
        "headers": headers,
        "footers": footers,
        "image_cell_spans": image_cell_spans,
    }


def verify_geometry(layout: dict[str, Any], ledger: dict[str, Any], errors: list[str]) -> None:
    root_tables = layout["tables"]
    identified = layout["identified_tables"]
    expected_grid = [4428, 5412]
    for representative in ledger.get("representative_types", []):
        caption = f"representative:{representative.get('id', '?')}"
        table = identified.get(caption)
        if table is None:
            errors.append(f"missing representative 45:55 table: {caption}")
            continue
        if table_grid(table) != expected_grid:
            errors.append(f"wrong 45:55 grid for {caption}: {table_grid(table)}")
        if table.find("./w:tr[1]/w:trPr/w:tblHeader", NS) is None:
            errors.append(f"missing repeated header row flag: {caption}")

    expected_occurrences = len(ledger.get("question_occurrences", [])) + sum(
        len(entry.get("question_ids", [])) for entry in ledger.get("prior_year_sequence", [])
    )
    occurrence_tables = [table for table in root_tables if table_caption(table).startswith("occurrence:")]
    if len(occurrence_tables) != expected_occurrences:
        errors.append(
            f"occurrence table count mismatch: expected {expected_occurrences}, found {len(occurrence_tables)}"
        )
    for table in occurrence_tables:
        caption = table_caption(table)
        if table_grid(table) != expected_grid:
            errors.append(f"wrong 45:55 grid for {caption}: {table_grid(table)}")
        if table.find("./w:tr[1]/w:trPr/w:tblHeader", NS) is None:
            errors.append(f"missing repeated header row flag: {caption}")

    if layout["image_cell_spans"] and any(span != 2 for span in layout["image_cell_spans"]):
        errors.append("one or more images are not in a full-width merged two-column row")


def verify_sections(root: ElementTree.Element, layout: dict[str, Any], ledger: dict[str, Any], errors: list[str]) -> None:
    section_props = root.findall(".//w:sectPr", NS)
    if not section_props:
        errors.append("DOCX has no section properties")
    for index, section in enumerate(section_props, start=1):
        size = section.find("./w:pgSz", NS)
        margin = section.find("./w:pgMar", NS)
        if size is None or size.get(attr("w")) != "11906" or size.get(attr("h")) != "16838":
            errors.append(f"section {index} is not A4 portrait")
        if margin is None:
            errors.append(f"section {index} lacks page margins")
        else:
            for side in ("left", "right"):
                value = int(margin.get(attr(side), "0"))
                if not 900 <= value <= 1021:
                    errors.append(f"section {index} {side} margin is outside 16-18 mm: {value}")

    header_text = "\n".join(layout["headers"])
    required_headers = {rep.get("lecture_unit", "강의 순서 단권화") for rep in ledger.get("representative_types", [])}
    required_headers.add("작년 기출 실전 순서")
    for required in required_headers:
        if required and required not in header_text:
            errors.append(f"missing running header: {required}")
    if any(text for text in layout["footers"]):
        errors.append("footer content exists although the layout contract requires header only")


def verify_plain_provenance(root: ElementTree.Element, errors: list[str]) -> None:
    prefixes = ("[원문", "[기출 통합 재구성", "[족보 참고", "[단권화 보충", "[AI 외부 보충", "[출처 확인 필요")
    for run in root.findall(".//w:r", NS):
        text = "".join(node.text or "" for node in run.findall(".//w:t", NS))
        if not text.lstrip().startswith(prefixes):
            continue
        r_pr = run.find("./w:rPr", NS)
        if r_pr is not None and r_pr.find("./w:color", NS) is not None:
            errors.append(f"provenance text uses color formatting: {text[:40]}")


def verify_no_visible_technical_ids(
    root: ElementTree.Element,
    parts: dict[str, ElementTree.Element],
    ledger: dict[str, Any],
    errors: list[str],
) -> None:
    internal_ids = {
        str(item.get("id"))
        for field in (
            "source_artifacts",
            "question_occurrences",
            "images",
            "representative_types",
            "semantic_atoms",
            "semantic_coverage",
            "second_pass_reviews",
            "audit_findings",
        )
        for item in ledger.get(field, [])
        if item.get("id")
    }
    generated_texts: list[str] = []
    for paragraph in root.findall(".//w:p", NS):
        text = visible_text(paragraph).strip()
        style = paragraph.find("./w:pPr/w:pStyle", NS)
        style_name = style.get(attr("val"), "") if style is not None else ""
        if style_name.startswith("Heading"):
            generated_texts.append(text)
        for run in paragraph.findall("./w:r", NS):
            run_text = "".join(node.text or "" for node in run.findall(".//w:t", NS))
            if run_text.lstrip().startswith("["):
                generated_texts.append(run_text)
    audit = next(
        (table for table in root.findall(".//w:tbl", NS) if table_caption(table) == "audit:coverage"),
        None,
    )
    if audit is not None:
        generated_texts.append(visible_text(audit))
    generated_texts.extend(visible_text(part) for part in parts.values())
    for doc_pr in root.findall(".//wp:docPr", NS):
        generated_texts.extend([doc_pr.get("title", ""), doc_pr.get("descr", "")])
    for internal_id in sorted(internal_ids):
        if any(internal_id in generated for generated in generated_texts):
            errors.append(f"technical ID is visible in generated study UI: {internal_id}")


def verify_compact_audit(root: ElementTree.Element, validation: dict[str, Any], errors: list[str]) -> None:
    table = next(
        (item for item in root.findall(".//w:tbl", NS) if table_caption(item) == "audit:coverage"),
        None,
    )
    if table is None:
        errors.append("missing compact semantic coverage audit")
        return
    text = visible_text(table)
    if any(label not in text for label in ("문제 완전성", "해설 완전성", "미해결", "상태")):
        errors.append("compact audit is missing required columns")
    for summary in validation.get("representative_coverage", []):
        required = (
            f"{summary.get('problem_mapped', 0)}/{summary.get('problem_required', 0)}",
            f"{summary.get('explanation_mapped', 0)}/{summary.get('explanation_required', 0)}",
            summary.get("title", ""),
        )
        if any(str(value) not in text for value in required):
            errors.append(f"compact audit totals missing for {summary.get('representative_type_id')}")


def verify_docx(docx_path: Path, ledger: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    root, parts = read_parts(docx_path)
    text = visible_text(root)
    drawing_count = len(root.findall(".//a:blip", NS))
    questions = ledger.get("question_occurrences", [])
    images = ledger.get("images", [])
    layout = inspect_layout(root, parts)
    from validate_ledger import validate_ledger

    validation = validate_ledger(ledger)
    if not validation.get("valid"):
        details = "; ".join(validation.get("errors", [])[:5])
        errors.append(f"ledger semantic completeness validation failed: {details}")

    for required_heading in (
        "제1부. 강의 순서 단권화",
        "제2부. 작년 기출 실전 순서",
        "제3부. 완전성 감사표",
    ):
        if required_heading not in text:
            errors.append(f"missing required heading: {required_heading}")

    for question in questions:
        question_id = question.get("id", "<missing>")
        for field in ("original_problem", "original_answer", "original_explanation"):
            value = question.get(field, "")
            if value and value not in text:
                errors.append(f"missing exact {field} for {question_id}")
        for index, choice in enumerate(question.get("original_choices", []), start=1):
            if choice and choice not in text:
                errors.append(f"missing exact choice {index} for {question_id}")

    for representative in ledger.get("representative_types", []):
        for field in ("problem_components", "choice_components", "answer_components", "explanation_components"):
            for component in representative.get(field, []):
                value = component.get("text", "")
                if value and value not in text:
                    errors.append(f"missing representative component {representative.get('id')}:{field}")
                for rationale in component.get("rationale_components", []):
                    rationale_text = rationale.get("text", "")
                    if rationale_text and rationale_text not in text:
                        errors.append(f"missing rationale for representative {representative.get('id')}")

    included_images = 0
    for image in images:
        image_id = image.get("id", "<missing>")
        if image.get("word_location"):
            included_images += 1
            artifact = next(
                (source for source in ledger.get("source_artifacts", []) if source.get("id") == image.get("source_artifact_id")),
                {},
            )
            label = f"[원문 · {artifact.get('file_name', '?')} · {image.get('source_page', '?')}쪽]"
            if label not in text:
                errors.append(f"missing human-readable image provenance for {image_id}")
        elif image.get("status") != "review_required":
            errors.append(f"image lacks Word location and review status: {image_id}")
    if drawing_count < included_images:
        errors.append(f"DOCX contains {drawing_count} drawings but ledger expects at least {included_images} included images")

    actual_prior = [
        table_caption(table)
        for table in layout["tables"]
        if table_caption(table).startswith("occurrence:part2:")
    ]
    expected_prior = [
        f"occurrence:part2:{entry.get('sequence')}:{question_id}"
        for entry in ledger.get("prior_year_sequence", [])
        for question_id in entry.get("question_ids", [])
    ]
    if actual_prior != expected_prior:
        errors.append("prior-year question order differs from ledger metadata")

    verify_geometry(layout, ledger, errors)
    verify_sections(root, layout, ledger, errors)
    verify_plain_provenance(root, errors)
    verify_no_visible_technical_ids(root, parts, ledger, errors)
    verify_compact_audit(root, validation, errors)

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
            "problem_tables_found": len(
                [table for table in layout["tables"] if table_caption(table).startswith(("representative:", "occurrence:"))]
            ),
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
