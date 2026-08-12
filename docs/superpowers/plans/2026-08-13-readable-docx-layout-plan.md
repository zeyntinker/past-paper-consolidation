# Readable DOCX Layout Implementation Plan

## Goal

Implement the approved A4 hybrid 45:55 problem–explanation layout without changing source selection, ledger semantics, completeness requirements, provenance rules, or the three-part output order.

## Baseline

Before editing, run:

```powershell
& $python -m unittest discover -s build-exam-master-note\tests -v
```

Record the existing passing count. Stop if the baseline is not green for reasons unrelated to this change.

## Task 1: Add layout-contract test helpers

Files:

- Modify `build-exam-master-note/tests/test_pipeline.py`
- Modify `build-exam-master-note/scripts/verify_docx.py`

Steps:

1. Add OOXML inspection helpers that read `word/document.xml`, section properties, tables, cell widths, table-header flags, row split controls, merges, headers, and footers without using the document builder's helper functions.
2. Add a failing test asserting A4 portrait dimensions, 16–18 mm side margins, a running header, and no generated footer content.
3. Add a failing test asserting that representative and year-specific tables use two columns with a 45:55 width ratio within a small OOXML rounding tolerance.
4. Add a failing test asserting repeated `문제 | 답·해설` header rows.
5. Run the new tests and confirm they fail for the intended missing layout behavior.

## Task 2: Implement page and table primitives

Files:

- Modify `build-exam-master-note/scripts/build_docx.py`

Steps:

1. Replace Letter page configuration with A4 portrait dimensions and 17 mm left/right margins.
2. Define constants for page geometry, usable width, 45:55 column widths, font sizes, cell margins, and paragraph spacing.
3. Generalize table geometry so the audit table and problem–explanation tables can use different total widths without hard-coded `9360` assumptions.
4. Add helpers for:
   - exact cell margins;
   - repeated table-header rows;
   - preventing row splits for short structural rows;
   - keeping headings with the next content block;
   - plain provenance typography;
   - two-column problem–explanation tables.
5. Run the Task 1 tests and make only the page/table primitive assertions pass.

## Task 3: Render representative types as exhaustive 45:55 tables

Files:

- Modify `build-exam-master-note/scripts/build_docx.py`
- Modify `build-exam-master-note/tests/test_pipeline.py`

Steps:

1. Extend fixtures to cover objective, essay, and short-answer representative types.
2. Add failing assertions that every representative problem component appears in the left cell and every explanation component appears in the right cell.
3. Add failing assertions that objective choices retain all distinct choices, verdicts, and rationale components.
4. Implement type-specific cell composition:
   - objective: answer, then every choice with O/X and full rationale;
   - essay: every subquestion and complete answer/scoring content;
   - short answer: prominent answer followed by its complete basis.
5. Preserve component order and provenance adjacency. Do not introduce a summary field or truncate component text.
6. Allow long explanation cells to flow across pages and repeat the table header.
7. Run representative-layout and existing ledger tests.

## Task 4: Render every year-specific original as a separate 45:55 table

Files:

- Modify `build-exam-master-note/scripts/build_docx.py`
- Modify `build-exam-master-note/tests/test_pipeline.py`
- Modify `build-exam-master-note/scripts/verify_docx.py`

Steps:

1. Add a fixture with identical repeated questions from multiple years.
2. Add failing assertions that each occurrence has its own table and occurrence ID.
3. Put exact original problem and choices in the left cell.
4. Put exact original answer and explanation in the right cell.
5. Preserve every original string byte-for-text after DOCX XML normalization; never substitute representative text.
6. Add spacing between occurrence tables without adding arbitrary page breaks.
7. Verify that repeated occurrences remain independently countable and locatable.

## Task 5: Add full-width image rows and conflict presentation

Files:

- Modify `build-exam-master-note/scripts/build_docx.py`
- Modify `build-exam-master-note/tests/test_pipeline.py`
- Modify `build-exam-master-note/scripts/verify_docx.py`

Steps:

1. Add image fixtures with known dimensions and aspect ratios.
2. Add a failing test that each related image appears in a merged two-column row immediately after its problem–explanation content and retains aspect ratio.
3. Add fixtures for a questionable original answer plus a separately sourced correction/supplement.
4. Render `원문 답` and `검토·보충` as separate labeled blocks.
5. Render `원문 답과 보충 판정 불일치` when the ledger explicitly represents a conflict; never infer away or overwrite either value.
6. Keep image and conflict provenance as plain black bracketed 8.5–9 pt italic text, with no color, fill, badge, icon, or border.
7. Verify image counts, relationships, order, merge geometry, and conflict strings independently.

## Task 6: Add running headers and safe pagination

Files:

- Modify `build-exam-master-note/scripts/build_docx.py`
- Modify `build-exam-master-note/tests/test_pipeline.py`
- Modify `build-exam-master-note/scripts/verify_docx.py`

Steps:

1. Add section/header helpers that display the current lecture unit in Part 1 and `작년 기출 실전 순서` in Part 2.
2. Ensure no table of contents or footer is generated.
3. Keep short tables together when possible; permit oversized content to split rather than shrink or disappear.
4. Keep a representative heading with its first table row.
5. Start representative types on new pages when doing so does not create excessive blank space; use deterministic `keep_with_next`/page-break rules rather than content deletion.
6. Add a long-explanation fixture and verify that all text survives pagination-related OOXML settings.

## Task 7: Update the reusable template and skill instructions

Files:

- Modify `build-exam-master-note/assets/master-note-template.docx`
- Modify `build-exam-master-note/SKILL.md`
- Add `build-exam-master-note/references/docx-layout-contract.md`

Steps:

1. Put the detailed layout contract in the new reference file so `SKILL.md` remains concise.
2. Link that reference from the DOCX build/verification step in `SKILL.md`.
3. Regenerate the template through the skill's deterministic `--create-template` path after the builder implements A4 and typography settings.
4. Confirm `agents/openai.yaml` still accurately describes the skill; do not regenerate it unless its interface text has become stale.
5. Run the official skill validator with UTF-8 mode.

## Task 8: End-to-end verification and visual QA

Files:

- Modify `build-exam-master-note/tests/test_pipeline.py` only if a discovered regression needs a new test
- Produce temporary artifacts only under ignored `test-output/`

Steps:

1. Run the complete unit suite.
2. Run Python compilation checks for all skill scripts.
3. Build a representative sample DOCX containing objective, essay, short-answer, repeated-year, long-explanation, image, and answer-conflict cases.
4. Run `scripts/verify_docx.py` independently against the sample ledger.
5. Render the sample DOCX using the installed documents skill's renderer and inspect every page at 100% zoom.
6. Check clipping, Korean glyphs, table continuation, repeated headers, image legibility, headings, whitespace, and provenance adjacency.
7. If rendering is unavailable or defective, report visual QA as failed or unavailable and do not claim the layout is fully verified.
8. Run `git diff --check`, inspect the final diff for unrelated changes, and confirm no generated/private course data is tracked.

## Task 9: Commit, distribute, and verify installations

Files:

- Commit only the reviewed skill, tests, template, and design/plan documentation.

Steps:

1. Commit the implementation locally with a focused message.
2. Show the test, validator, independent DOCX verification, and visual-QA results.
3. After authorization, push `main` to `https://github.com/zeyntinker/past-paper-consolidation`.
4. Reinstall the GitHub version to:
   - `C:\Users\danie\.codex\skills\build-exam-master-note`
   - `C:\Users\danie\.gemini\config\skills\build-exam-master-note`
5. Compare all tracked installed files against the pushed Git blob IDs and run the official skill validator on both installed directories.

## Acceptance criteria

- The document is A4 portrait with the approved typography and header-only navigation.
- Every representative and year-specific occurrence uses the approved adaptive 45:55 structure.
- Representative explanations remain exhaustive; no summarization or shortening is introduced.
- Every original occurrence, explanation, repetition, image, and provenance label remains accounted for.
- Images use full-width merged rows unless genuinely icon-sized.
- Wrong or questionable original answers remain visible beside separate supplements and conflicts.
- Deterministic tests and independent DOCX verification pass.
- Rendered visual QA passes before the implementation is described as complete.
