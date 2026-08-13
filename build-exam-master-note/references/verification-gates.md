# Verification gates

## Complete status requirements

All conditions must pass:

- Approved manifest fingerprint equals the current inventory fingerprint.
- Every included file has matching name, size, and SHA-256.
- Every source page is processed.
- Every question occurrence is recorded and has a Word location.
- Every original problem, choice, answer, and explanation matches the source string.
- Every image has a Word location or an explicit review finding.
- Every representative component has valid provenance and an internal component ID.
- Every required problem atom maps to a visible representative problem/choice component.
- Every required original-explanation and relevant lecture-note atom maps to a visible answer/rationale/explanation component.
- Every representative has a complete independent second-pass reread with no unresolved atom.
- Every representative has all five synthesis-quality checks explicitly true.
- Every representative problem contains substantive problem text, not only a number, ID, answer, or provenance label.
- Every representative answer is a coherent integrated solution rather than a source list, generic narration, or short summary.
- Every objective choice has a verdict and sourced rationale.
- Lecture ordering follows date then period.
- Prior-year sequence matches the order authority.
- Ledger and DOCX question/image counts agree.
- Independent DOCX verification passes.
- Rendered PNG inspection passes on every page.
- No blocking findings remain.

## Blocking findings

Use `review_required` for inventory changes, unsupported/corrupt/encrypted files, unprocessed pages, unreadable date/period, low-confidence OCR, broken Korean encoding, ambiguous question-bank boundaries, paired-format conflicts, reconstruction/explanation conflicts, ambiguous image relationships, missing provenance, ledger-DOCX mismatches, or render defects.

## Failure behavior

1. Do not hide successful work.
2. Produce a review-required draft only when structurally safe.
3. List every blocking finding with source file, page, item ID, and required decision.
4. Include source-page evidence for visual ambiguities.
5. Never change source text automatically to make validation pass.

## Independent verification

The verification pass reads the final DOCX and ledger without trusting the generation process. It uses internal IDs only through non-visible OOXML metadata. It checks exact source strings, image counts, sequence order, human-readable provenance labels, semantic coverage totals, and the compact audit summary. Generated technical IDs in visible headings, provenance, captions, headers, or audit rows are a failure. A failure returns the run to the earliest affected stage.
