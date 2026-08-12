# Readable DOCX Layout Design

## Objective

Improve the generated exam master-note DOCX for rapid study without weakening the skill's existing completeness, exact-original, provenance, repetition-preservation, or fail-closed requirements. Change presentation only: do not summarize or remove required content to make the document shorter.

## Chosen approach

Use an adaptive hybrid layout. Put problems and their corresponding answers/explanations in a two-column table when side-by-side comparison helps. Put large images in a full-width merged row directly below the related table. Allow long explanations to continue across pages instead of abbreviating them.

Rejected alternatives:

- An all-two-column layout makes long prompts and images too narrow.
- An all-vertical card layout preserves width but slows repeated problem-to-explanation comparison.

## Page and typography

- Use A4 portrait pages.
- Use left and right margins between 16 mm and 18 mm.
- Use Malgun Gothic at 10 pt for table and body content.
- Use 10.5–11 pt bold text for problem titles and answer labels.
- Use 8.5–9 pt italic text for provenance labels.
- Use approximately 1.15 line spacing.
- Use approximately 2.0 mm vertical and 2.5 mm horizontal cell padding.
- Do not reduce ordinary content below 10 pt merely to reduce page count.
- Do not create a table of contents or footer.
- Put only the current lecture unit or `작년 기출 실전 순서` in the running header.

## Representative types

Create one 45:55 table for each representative type:

- Left 45%: the complete representative problem, every distinct objective choice, or every essay subquestion.
- Right 55%: the complete explanation, not a summary.

The complete explanation must exhaustively integrate every relevant point from all linked question-bank explanations and the relevant lecture-note material. Do not shorten it to key points. If it becomes longer than a page, continue it across pages.

Structure content by question type while retaining the same outer table:

- Objective: show the answer, then an O/X verdict and detailed rationale for every choice.
- Essay: show the complete answer and every supported scoring point for all subquestions.
- Short answer: show the answer prominently, followed by the complete basis.

Organize the complete explanation in this order when applicable:

1. Answer or conclusion.
2. Choice-by-choice rationale or subquestion-by-subquestion answer.
3. Detailed related concepts.
4. Exceptions and differential points.
5. Memorization cautions supported by the source material.

Do not invent unsupported scoring points or memorization cautions. Apply the established supplement provenance when material is not original question-bank text.

## Year-specific originals

Keep every linked occurrence, including identical repetitions across years. For each occurrence, create a separate 45:55 table:

- Left 45%: that occurrence's exact original problem and choices.
- Right 55%: that occurrence's exact original answer and explanation.

This intentional duplication provides both an integrated study explanation and independently auditable year-specific evidence. Never replace the original occurrence with the representative version.

## Images

- Put related images immediately below the corresponding problem–explanation table.
- Use a full-width merged row and preserve the image's aspect ratio.
- Keep each image's provenance text immediately below it.
- Permit an image inside a normal column only when it is genuinely icon-sized and remains legible.
- Keep ambiguous image relationships as review-required evidence under the existing rules.

## Pagination

- Keep a short problem–explanation table together on one page.
- Permit a table longer than one page to continue naturally.
- Repeat the `문제 | 답·해설` column header on every continuation page.
- Keep a problem title with the first content row.
- Add clear spacing between year-specific occurrences.
- Start a new representative type on a new page when practical, but do not create excessive blank space.

## Provenance and answer conflicts

Preserve the existing provenance vocabulary and exact-original rules:

- `[원문 · file · page · question ID]`
- `[AI 복원 · 기출 근거 IDs]`
- `[족보 보충 · file · page]`
- `[단권화 보충 · representative ID]`
- `[AI 외부 보충 · authoritative source]`
- `[출처 확인 필요]`

Render provenance as plain black bracketed text at 8.5–9 pt, italicized for separation from body text. Do not use colored text, badges, icons, fills, or borders. Place the provenance immediately after or directly below the content span it supports.

Never label modified text as original. Preserve a questionable or wrong original answer unchanged. In the answer/explanation column, separate `원문 답` from `검토·보충`. If they conflict, display `원문 답과 보충 판정 불일치` without deleting or overwriting either value. Unverifiable content remains `[출처 확인 필요]` and blocks `complete` status.

## Implementation boundaries

Update only the layout-related portions of the existing skill:

- Extend `scripts/build_docx.py` with reusable table, pagination, header, image-row, and question-type rendering helpers.
- Update `assets/master-note-template.docx` to match the A4 and typography rules.
- Extend `scripts/verify_docx.py` to inspect layout-critical OOXML independently.
- Extend `tests/test_pipeline.py` with objective, essay, short-answer, long-explanation, image, and conflicting-answer fixtures.
- Update the skill instructions or a directly linked reference only where necessary to make the layout contract discoverable.

Do not change source selection, manifest approval, normalization, ledger semantics, completeness accounting, or the three-part document order.

## Verification and completion

Automated verification must establish that:

- Every representative type and year-specific occurrence has the required 45:55 problem–explanation table.
- Every required original string and every complete-explanation component remains in the DOCX.
- All provenance labels remain present and adjacent to their supported content.
- Image count, ordering, provenance, aspect ratio, and full-width placement are correct.
- The document uses A4 portrait dimensions, the running header only, repeated table headers, required cell widths, and safe row/page-break settings.
- Objective, essay, short-answer, long-explanation, image, repeated-year, and conflicting-answer cases pass.

Render the finished DOCX and inspect every page for clipping, missing glyphs, broken tables, unreadable images, orphan headings, and excessive blank space. A render defect or deterministic mismatch keeps the result in `review_required`; it must never be reported as `complete`.
