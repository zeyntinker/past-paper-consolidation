# DOCX Layout Contract

Use the `compact_reference_guide` design preset with the named overrides below. The user's approved layout overrides the preset where they conflict.

## Page and type

- Use A4 portrait pages with 17 mm left/right margins and 20 mm top/bottom margins.
- Use Malgun Gothic 10 pt for ordinary body and table text with 1.15 line spacing.
- Use 10.5–11 pt bold labels for problem titles and answer labels.
- Use 8.5–9 pt italic black text for provenance.
- Do not add a table of contents or footer.
- Use a running header containing the current lecture unit in Part 1, `작년 기출 실전 순서` in Part 2, and `완전성 감사표` in Part 3.

## Problem–explanation tables

Use a fixed-width two-column table for every representative type and every year-specific occurrence:

- Left column: 45%, labeled `문제`.
- Right column: 55%, labeled `답·해설`.
- Repeat the column-header row when a table continues on another page.
- Keep short content rows together. Permit long content rows to flow across pages; never shrink, truncate, or summarize content to prevent a page break.

For each representative type:

- Put the complete reconstructed problem and every distinct choice or subquestion in the left cell.
- Put the complete explanation in the right cell.
- Treat both cells as coherent reconstructions. Do not list source problems or concatenate source explanations.
- For objective questions, include every choice's O/X verdict and detailed rationale.
- For essay questions, include the complete answer and every supported scoring point.
- For short-answer questions, show the answer followed by its complete basis.
- Exhaustively integrate all linked question-bank explanations and all relevant lecture-note content. Do not output a short or key-point-only explanation.
- Every required semantic atom must map to an internal component rendered in the applicable cell before the document can be complete.

For each year-specific occurrence:

- Put that occurrence's exact original problem and choices in the left cell.
- Put that occurrence's exact original answer and explanation in the right cell.
- Keep every repeated occurrence as its own table, even when wording is identical across years.

## Images

- Add related images immediately below their problem–explanation row in a merged full-width row.
- Preserve aspect ratio and keep the provenance immediately below the image.
- Use a normal column only for genuinely icon-sized images that remain legible.
- Keep ambiguous image relationships as review-required evidence.

## Provenance and conflicts

- Render the complete bracketed provenance wording as plain black 8.5–9 pt italic text.
- Do not use colored text, badges, icons, fills, or borders for provenance.
- Place each label immediately after or directly below the content it supports.
- Never label modified text as `[원문]`.
- Show only human-readable file/year/page, lecture unit, and representative title in provenance. Never display internal representative, question, image, atom, component, or audit IDs.
- Preserve questionable original answers unchanged under `원문 답`.
- Put separate sourced corrections or supplementation under `검토·보충`.
- When they conflict, display `원문 답과 보충 판정 불일치` and retain both.

## Pagination and verification

- Keep each representative heading with its first table row.
- Start a new representative type on a new page when practical without deleting content or creating deliberate blank pages.
- Leave visible spacing between year-specific occurrence tables.
- Independently verify A4 section geometry, 45:55 table grids, repeated header flags, full-width image rows, header-only navigation, exact original strings, exhaustive explanation components, and plain provenance formatting.
- Treat any deterministic mismatch or rendered defect as `review_required`.
