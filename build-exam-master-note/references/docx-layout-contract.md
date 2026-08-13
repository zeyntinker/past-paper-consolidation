# DOCX Layout Contract

Use the `compact_reference_guide` design preset with the named overrides below. The user's approved layout overrides the preset where they conflict.

## Page and type

- Use A4 portrait pages with 10 mm left/right margins and 20 mm top/bottom margins.
- Use Malgun Gothic 7 pt for every visible character without exception: title, heading, running header, table header, body, label, provenance, caption, and audit text.
- Create hierarchy only with bold weight, spacing, borders, and grayscale cell shading. Never enlarge text above 7 pt.
- Do not add a table of contents or footer.
- Use a running header containing the current lecture unit in Part 1, `작년 기출 실전 순서` in Part 2, and `완전성 감사표` in Part 3.

## Problem–explanation tables

Use one fixed-width three-column table per representative type:

- First column: 12%, labeled `구분 / 연도`.
- Second column: 43%, labeled `문제`.
- Third column: 45%, labeled `해설`.
- Repeat the column-header row when a table continues on another page.
- Keep short content rows together. Permit long content rows to flow across pages; never shrink, truncate, or summarize content to prevent a page break.
- Put the representative row first with `[대표유형 - 문제유형]` in column 1.
- Put every linked year/round occurrence in the rows immediately below it. Do not create separate occurrence tables or headings.

For each representative type:

- Put the complete reconstructed problem and every distinct choice or subquestion in the left cell.
- Put the complete explanation in the right cell.
- Treat both cells as coherent reconstructions. Do not list source problems or concatenate source explanations.
- For objective questions, include every choice's O/X verdict and detailed rationale.
- For essay questions, include the complete answer and every supported scoring point.
- For short-answer questions, show the answer followed by its complete basis.
- Exhaustively integrate all linked question-bank explanations and all relevant lecture-note content. Do not output a short or key-point-only explanation.
- Every required semantic atom must map to an internal component rendered in the applicable cell before the document can be complete.
- Reject a representative problem whose visible content is empty, only a problem number, only an ID, or only a source label.
- Structure the explanation as `정답/모범답안 → 풀이·근거 → 선지별 판정 또는 채점 요소 → 관련 개념·예외·주의점 → 암기 포인트` as applicable. Use short paragraphs and bold 7 pt labels, not one unbroken paragraph.
- Reject `해설 참조`, source lists, generic study advice, unsupported narration, or a short summary as a complete explanation.

For each year-specific occurrence row:

- Put that occurrence's exact original problem and choices in the left cell.
- Put that occurrence's exact original answer and explanation in the right cell.
- Keep every repeated occurrence as its own row, even when wording is identical across years.

## Images

- Keep a small problem image in the problem cell and a small explanatory diagram in the explanation cell only when it remains legible.
- Otherwise add it immediately below its problem–explanation row in a merged full-width three-column row.
- Preserve aspect ratio and keep the provenance immediately below the image.
- Use a normal column only for genuinely icon-sized images that remain legible.
- Keep ambiguous image relationships as review-required evidence.

## Provenance and conflicts

- Render the complete bracketed provenance wording as plain black 7 pt italic text.
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
- Independently verify A4 section geometry, 10 mm side margins, 12:43:45 table grids, uniform 7 pt text, repeated header flags, full-width image rows, header-only navigation, exact original strings, exhaustive explanation components, and plain provenance formatting.
- Treat any deterministic mismatch or rendered defect as `review_required`.
