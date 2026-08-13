# Representative Synthesis and Semantic Completeness Implementation Plan

## Goal

Implement the approved representative-synthesis design so that a `complete` result proves two separate claims:

1. every required source element is represented in one coherent representative problem; and
2. every original-explanation meaning and every relevant lecture-note meaning is absorbed into one logical, complete representative answer.

Keep every year-specific original unchanged below the representative type. Hide technical IDs from visible study content, retain them in the machine ledger and non-visible OOXML metadata, and keep Part 3 compact.

## Baseline and constraints

Before editing:

```powershell
python -m unittest discover -s build-exam-master-note\tests -v
python -m compileall -q build-exam-master-note\scripts build-exam-master-note\tests
git diff --check
```

Record the passing-test count. Stop and investigate if the baseline fails for an unrelated reason.

Do not change:

- the two-link scope;
- `합본` exclusion;
- PDF/HWP/HWPX selection and normalization;
- chronological date-then-period ordering;
- prior-year source ordering;
- immutable-original and repeated-year preservation;
- image-preservation or fail-closed rules;
- A4, header-only, no-TOC, 45:55 table, and full-width-image layout.

## Task 1: Add semantic-coverage fixtures and failing tests

Files:

- Modify `build-exam-master-note/tests/test_pipeline.py`

Steps:

1. Refactor the common ledger fixture so every representative output component has an internal component ID.
2. Add source-atom fixtures for:
   - stem conditions, numbers, qualifiers, objective choices, essay subquestions, and image findings;
   - original-answer and original-explanation meanings;
   - relevant and excluded lecture-note meanings;
   - semantically duplicate meanings from multiple sources;
   - conditionally different meanings that must not be merged;
   - unresolved conflicts and ambiguous relevance decisions.
3. Add a recorded second-pass reread fixture containing reviewed source/page scope, newly discovered atoms, unresolved items, and final status.
4. Add failing validator tests proving that each of the following blocks completion independently:
   - an unmapped problem atom;
   - an unmapped original-explanation atom;
   - an unmapped relevant lecture-note atom;
   - an atom mapped only to a year-specific original;
   - a missing or incomplete second-pass reread;
   - a pending relevance decision;
   - a hidden or unresolved conflict;
   - an external supplement without a usable citation/locator.
5. Add passing tests showing that duplicate atoms may map to one output component with all source links retained, while conditional differences map to separate visible components.
6. Run only the new tests and confirm that they fail for the intended missing schema/validator behavior.

## Task 2: Extend the ledger schema and protocol references

Files:

- Modify `build-exam-master-note/references/provenance-schema.md`
- Modify `build-exam-master-note/references/lecture-master-note-protocol.md`
- Modify `build-exam-master-note/references/prior-year-exam-protocol.md`
- Modify `build-exam-master-note/references/verification-gates.md`

Steps:

1. Add internal IDs to representative problem, choice, answer, rationale, and explanation components.
2. Define `semantic_atoms[]` with required fields:
   - `id`;
   - `representative_type_id`;
   - `category`: `problem`, `original_explanation`, or `lecture_note`;
   - `atom_type`: stem, condition, choice, subquestion, answer, rationale, definition, mechanism, finding, image, criterion, differential, treatment, indication, contraindication, prognosis, exception, trap, prerequisite, or other narrowly described type;
   - source artifact/page and, where applicable, source question/field/image;
   - exact source text or image reference;
   - `relevance_status`: `required`, `excluded`, or `review_required`;
   - optional duplicate/conflict group references;
   - provenance kind and review status.
3. Define `semantic_coverage[]` with `atom_id`, representative target kind, target component IDs, integration mode (`exact`, `synthesized`, `duplicate_merged`, or `conditional_split`), and coverage status.
4. Define `second_pass_reviews[]` per representative with reviewed source/page scope, discovered atom IDs, unresolved atom IDs, reviewer notes, and status.
5. Require a written exclusion reason for lecture-note atoms marked `excluded`; `review_required` is never treated as excluded.
6. State that all technical IDs are ledger-only and never learner-facing.
7. Clarify that Part 2 originals come from the second-link prior-year corpus; Part 1 and then external sources may supplement them only with visible non-original provenance.
8. Update the completion gate: structural validation plus a recorded source reread are both mandatory; counts and substring checks alone are insufficient.

## Task 3: Implement fail-closed semantic validation

Files:

- Modify `build-exam-master-note/scripts/validate_ledger.py`
- Modify `build-exam-master-note/scripts/common.py` only if shared enums/constants are needed
- Modify `build-exam-master-note/tests/test_pipeline.py`

Steps:

1. Validate uniqueness and referential integrity for component IDs, semantic atom IDs, coverage records, duplicate groups, conflict groups, and second-pass reviews.
2. Validate atom source locators against artifacts, occurrences, pages, fields, and images.
3. Require every `required` problem atom to map to a problem or choice component of the same representative.
4. Require every `required` original-explanation or lecture-note atom to map to an answer, rationale, or explanation component of the same representative.
5. Reject mappings that point only to year-specific originals or to a different representative.
6. Allow multiple duplicate atoms to target one component, but require every atom to have its own mapping record and source locator.
7. Require conflicting or conditionally distinct atoms to remain separately represented unless the conflict is explicitly unresolved; unresolved conflicts force `review_required`.
8. Require each objective choice component to have a verdict and sourced rationale, and require every source choice atom to be covered.
9. Require every essay subquestion and supported scoring-point atom to be covered.
10. Validate that the second pass covers the full applicable normalized source/page scope, accounts for newly found atoms, and contains no unresolved required atom before returning `complete_candidate`.
11. Return compact per-representative coverage counts in the validation report: required/mapped problem atoms, required/mapped explanation atoms, unresolved count, and status.
12. Run the Task 1 tests and existing provenance/original-preservation tests until green.

## Task 4: Make coherent synthesis mandatory in the skill instructions

Files:

- Modify `build-exam-master-note/SKILL.md`
- Modify `build-exam-master-note/references/lecture-master-note-protocol.md`
- Modify `build-exam-master-note/references/docx-layout-contract.md`

Steps:

1. Add a prominent non-negotiable rule that the representative problem is one completed problem, not an original-question list.
2. Add a prominent non-negotiable rule that the representative explanation is one logical and systematic complete answer, not a summary, excerpt collection, or source-by-source concatenation.
3. Require exhaustive absorption of problem-bank explanations and relevant lecture-note material, including all conditions, exceptions, rationales, and scoring points.
4. Define objective, essay, short-answer, fragmentary, duplicate, conditional-conflict, and unresolved-conflict handling in concise operational language.
5. Require atomization before synthesis and the independent source reread after synthesis.
6. Require narrow external supplementation only after the supplied corpus is exhausted.
7. Link the detailed schema and verification-gate references rather than duplicating their full field definitions in `SKILL.md`.

## Task 5: Remove visible technical IDs and render human-readable provenance

Files:

- Modify `build-exam-master-note/scripts/build_docx.py`
- Modify `build-exam-master-note/tests/test_pipeline.py`

Steps:

1. Remove representative IDs from visible representative headings.
2. Remove question IDs from visible year-specific headings, problem/answer labels, and provenance.
3. Remove image IDs from visible image captions and provenance.
4. Replace learner-facing labels with file/year/page wording, including:
   - `[원문 · 2024 기출.pdf · 12쪽]`;
   - `[기출 통합 재구성 · 2022년·2024년 기출 참고]`;
   - `[족보 참고 · 강의정리.pdf · 31쪽]`;
   - `[단권화 보충 · 강의 단원 · 대표문제 제목]`;
   - `[AI 외부 보충 · source]`;
   - `[출처 확인 필요]`.
5. Preserve the exact `[원문]` rule: reconstructed or modified text never receives an original label.
6. Keep internal IDs in non-visible `w:tblCaption` values and other deterministic metadata required by the verifier.
7. Do not treat an ID-like string that genuinely occurs inside immutable original source text as generated technical clutter; preserve the original unchanged.
8. Add tests inspecting visible OOXML text separately from captions/metadata.

## Task 6: Render the compact Part 3 audit

Files:

- Modify `build-exam-master-note/scripts/build_docx.py`
- Modify `build-exam-master-note/tests/test_pipeline.py`

Steps:

1. Replace the current general findings dump for normal representative items with one compact row containing:
   - human-readable lecture unit/title;
   - problem coverage;
   - explanation coverage;
   - unresolved count;
   - status.
2. Do not show representative, question, atom, or audit-finding IDs.
3. For passing representatives, show only counts/status.
4. For missing, conflicting, or review-required representatives, add one concise detail row with the affected human-readable source file/page and issue summary.
5. Keep the full atom mapping, source excerpts, and normal passing details exclusively in the ledger.
6. Add assertions that Part 3 stays compact when all items pass and expands only for exceptions.

## Task 7: Update independent DOCX verification

Files:

- Modify `build-exam-master-note/scripts/verify_docx.py`
- Modify `build-exam-master-note/tests/test_pipeline.py`

Steps:

1. Continue locating representative and occurrence tables by non-visible captions, not learner-facing IDs.
2. Replace visible question-ID presence checks with caption/order checks plus exact-original text verification.
3. Verify prior-year order using occurrence-table caption order rather than visible IDs.
4. Replace visible image-ID checks with image relationship/count, table association, and human-readable caption verification.
5. Inspect generated headings, provenance paragraphs, audit rows, headers, and image captions to ensure they do not expose ledger IDs.
6. Exempt immutable source text from ID-pattern rejection so genuine original wording is never altered.
7. Verify every human-readable provenance label is plain black bracketed text adjacent to its component.
8. Verify the compact Part 3 counts against validator-derived coverage totals.
9. Retain all existing A4, header, footer, 45:55, repeated-row, full-width-image, exact-original, and drawing-count checks.

## Task 8: End-to-end and visual verification

Files:

- Modify `build-exam-master-note/tests/test_pipeline.py` only when a discovered regression needs a test
- Produce temporary artifacts only under ignored test-output paths

Steps:

1. Run the full unit suite.
2. Run Python compilation checks.
3. Run the official skill validator in UTF-8 mode.
4. Build a sample ledger/DOCX containing:
   - duplicate and conditional source meanings;
   - objective, essay, and short-answer representatives;
   - a long complete explanation;
   - repeated year-specific originals;
   - original and lecture-note images;
   - prior-year supplements;
   - one resolved conflict and one separate review-required negative fixture.
5. Run `validate_ledger.py` and `verify_docx.py` independently.
6. Use the documents workflow to render the DOCX and inspect every page for clipping, Korean glyph corruption, misplaced provenance, broken tables, unreadable images, orphan headings, excessive whitespace, and accidentally visible IDs.
7. Confirm that long answers continue across pages without abbreviation.
8. Run `git diff --check` and inspect the final diff for unrelated or private course data.

## Task 9: Commit, publish, install, and compare

Files:

- Commit only the skill, tests, template if changed, and approved design/plan documentation.

Steps:

1. Commit the implementation with a focused message after all local checks pass.
2. Push `main` to `https://github.com/zeyntinker/past-paper-consolidation` as previously requested.
3. Install the resulting `build-exam-master-note` skill into:
   - `C:\Users\danie\.codex\skills\build-exam-master-note`;
   - `C:\Users\danie\.gemini\config\skills\build-exam-master-note`.
4. Run the official skill validator on both installed copies.
5. Compare every tracked installed file with the committed Git blobs or hashes.
6. If environment permissions prevent publishing or either installation, report the exact blocked step without claiming deployment completion; retain the verified repository implementation.

## Final acceptance criteria

- Every required problem atom maps to the coherent representative problem.
- Every required original-explanation and relevant lecture-note atom maps to the coherent representative answer.
- Duplicate meanings are written once but retain every source mapping.
- Conditional differences and exceptions remain explicit.
- Unresolved conflicts, ambiguous relevance, unreadable sources, missing mappings, or missing second-pass evidence block completion.
- Representative problems and explanations are complete reconstructions, not summaries or source lists.
- Every year-specific original and repeated occurrence remains unchanged and independently present.
- The learner sees human-readable provenance but no generated representative/question/atom IDs.
- The ledger retains all internal IDs and full mappings.
- Part 3 is compact for passing items and expands only for review cases.
- Automated tests, independent ledger/DOCX validation, rendered visual QA, skill validation, publication, and both installations succeed before the work is reported as fully complete.
