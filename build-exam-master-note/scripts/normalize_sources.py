#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from common import save_json, sha256_file, stable_id


def text_integrity_findings(text: str, file_name: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    replacement_count = text.count("\ufffd")
    suspicious_runs = len(re.findall(r"\?{3,}|�{2,}", text))
    if replacement_count or suspicious_runs:
        findings.append(
            {
                "id": stable_id("F", file_name, "encoding"),
                "severity": "blocking",
                "code": "TEXT_ENCODING_CORRUPTION",
                "message": (
                    f"Possible encoding corruption in {file_name}: "
                    f"replacement={replacement_count}, suspicious_runs={suspicious_runs}"
                ),
                "source_locations": [file_name],
                "status": "open",
            }
        )
    return findings


def extract_pdf(path: Path, out_dir: Path, render_pages: bool) -> dict[str, Any]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required to normalize PDFs") from exc

    reader = PdfReader(str(path))
    if reader.is_encrypted:
        raise RuntimeError("encrypted PDF is not supported")
    pages: list[dict[str, Any]] = []
    image_dir = out_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        image_records: list[dict[str, Any]] = []
        try:
            for image_index, image in enumerate(page.images, start=1):
                extension = Path(image.name).suffix or ".bin"
                image_name = f"page-{page_number:04d}-image-{image_index:03d}{extension}"
                image_path = image_dir / image_name
                image_path.write_bytes(image.data)
                image_records.append(
                    {
                        "id": stable_id("IMG", path.name, page_number, image_index),
                        "source_page": page_number,
                        "path": str(image_path),
                        "source_kind": "embedded_pdf_image",
                    }
                )
        except Exception as exc:  # pypdf image codecs vary by source PDF
            image_records.append(
                {
                    "id": stable_id("IMGERR", path.name, page_number),
                    "source_page": page_number,
                    "path": "",
                    "source_kind": "image_extraction_error",
                    "error": str(exc),
                }
            )
        pages.append(
            {
                "page": page_number,
                "text": text,
                "images": image_records,
                "text_integrity_findings": text_integrity_findings(text, f"{path.name} page {page_number}"),
            }
        )

    rendered_pages: list[str] = []
    if render_pages:
        pdftoppm = shutil.which("pdftoppm")
        if not pdftoppm:
            raise RuntimeError("pdftoppm is required when --render-pages is used")
        render_dir = out_dir / "page-renders"
        render_dir.mkdir(parents=True, exist_ok=True)
        prefix = render_dir / "page"
        completed = subprocess.run(
            [pdftoppm, "-png", "-r", "150", str(path), str(prefix)],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"pdftoppm failed: {completed.stderr.strip()}")
        rendered_pages = [str(p) for p in sorted(render_dir.glob("page-*.png"))]
        if len(rendered_pages) != len(pages):
            raise RuntimeError(
                f"rendered page count mismatch: expected {len(pages)}, got {len(rendered_pages)}"
            )

    return {
        "format": "pdf",
        "page_count": len(pages),
        "pages": pages,
        "rendered_pages": rendered_pages,
    }


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def extract_hwpx(path: Path, out_dir: Path) -> dict[str, Any]:
    pages: list[dict[str, Any]] = []
    image_records: list[dict[str, Any]] = []
    image_dir = out_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as archive:
        section_names = sorted(
            name
            for name in archive.namelist()
            if re.match(r"Contents/section\d+\.xml$", name, flags=re.IGNORECASE)
        )
        for section_index, section_name in enumerate(section_names, start=1):
            root = ElementTree.fromstring(archive.read(section_name))
            chunks: list[str] = []
            for element in root.iter():
                if local_name(element.tag) in {"t", "text"} and element.text:
                    chunks.append(element.text)
            text = "".join(chunks)
            pages.append(
                {
                    "page": section_index,
                    "text": text,
                    "images": [],
                    "text_integrity_findings": text_integrity_findings(
                        text, f"{path.name} section {section_index}"
                    ),
                }
            )

        media_names = sorted(
            name
            for name in archive.namelist()
            if name.casefold().startswith("bindata/") and not name.endswith("/")
        )
        for index, media_name in enumerate(media_names, start=1):
            media_path = image_dir / Path(media_name).name
            media_path.write_bytes(archive.read(media_name))
            image_records.append(
                {
                    "id": stable_id("IMG", path.name, media_name),
                    "source_page": None,
                    "path": str(media_path),
                    "source_kind": "hwpx_bindata_unmapped",
                }
            )
    return {
        "format": "hwpx",
        "page_count": None,
        "section_count": len(pages),
        "pages": pages,
        "unmapped_images": image_records,
        "rendered_pages": [],
        "audit_findings": [
            {
                "id": stable_id("F", path.name, "hwpx-layout"),
                "severity": "blocking",
                "code": "HWPX_PAGE_LAYOUT_UNVERIFIED",
                "message": (
                    "HWPX XML sections are not physical pages. Resolve this finding with "
                    "a paired PDF or a verified rendered conversion before completion."
                ),
                "source_locations": [path.name],
                "status": "open",
            }
        ],
    }


def convert_hwp_to_pdf(path: Path, out_dir: Path) -> Path:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise RuntimeError("HWP requires LibreOffice/soffice conversion, but it is unavailable")
    convert_dir = out_dir / "converted"
    convert_dir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(convert_dir), str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    candidate = convert_dir / f"{path.stem}.pdf"
    if completed.returncode != 0 or not candidate.exists():
        raise RuntimeError(f"HWP conversion failed: {completed.stderr.strip()}")
    return candidate


def normalize(path: Path, out_dir: Path, render_pages: bool) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    extension = path.suffix.casefold()
    base = {
        "schema_version": 1,
        "source_file": str(path),
        "file_name": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "status": "normalized",
        "audit_findings": [],
    }
    try:
        if extension == ".pdf":
            extracted = extract_pdf(path, out_dir, render_pages)
        elif extension == ".hwpx":
            extracted = extract_hwpx(path, out_dir)
        elif extension == ".hwp":
            converted = convert_hwp_to_pdf(path, out_dir)
            extracted = extract_pdf(converted, out_dir, render_pages)
            extracted["format"] = "hwp_via_pdf"
            extracted["converted_pdf"] = str(converted)
        else:
            raise RuntimeError(f"unsupported extension: {extension}")
        base.update(extracted)
        base.setdefault("audit_findings", [])
        for page in base.get("pages", []):
            base["audit_findings"].extend(page.get("text_integrity_findings", []))
        if base["audit_findings"]:
            base["status"] = "review_required"
    except Exception as exc:
        base["status"] = "review_required"
        base["audit_findings"].append(
            {
                "id": stable_id("F", path.name, "normalization"),
                "severity": "blocking",
                "code": "NORMALIZATION_FAILED",
                "message": str(exc),
                "source_locations": [path.name],
                "status": "open",
            }
        )
    return base


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize PDF, HWP, or HWPX without changing originals")
    parser.add_argument("source")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--render-pages", action="store_true")
    args = parser.parse_args()
    report = normalize(Path(args.source), Path(args.out_dir), args.render_pages)
    save_json(args.report, report)
    print(report["status"])
    return 0 if report["status"] == "normalized" else 2


if __name__ == "__main__":
    sys.exit(main())
