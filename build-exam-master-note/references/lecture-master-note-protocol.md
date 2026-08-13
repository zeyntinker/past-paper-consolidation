# Lecture-order master-note protocol

## Scope and ordering

Use only approved, non-`합본` files from link 1. Process by filename date ascending and first-page period ascending. A missing date or period is blocking; keep the file in the ledger and temporary review position.

## Exhaustive extraction

1. Inspect every page, not only extracted text.
2. Locate question-bank sections using headings, numbering, choices, O/X markers, answer/explanation markers, and visual blocks.
3. Register every candidate question before grouping.
4. Include ambiguous candidates as `[기출 여부 검수 필요]`.
5. Preserve the entire original problem, choices, answer, explanation, and associated image.
6. Record file, page, page location, source order, and year.
7. Compare the candidate count with visible page evidence before continuing.

Never discard malformed, incomplete, duplicated, or apparently incorrect material.

## Representative types

Group only questions with the same tested concept and intent. Do not merge merely because they share a broad chapter.

The representative problem and explanation are synthesis surfaces, not places to list originals. Before writing either one, atomize every source problem element, every original-explanation meaning, and every relevant lecture-note meaning using the ledger schema.

For each group:

1. Create one coherent, complete synthetic problem. It may reorganize supported wording and order, but it must not add a new tested point.
2. Mark reconstructed text with human-readable source years/files, never internal IDs.
3. Put every year-specific source occurrence below it with `[원문]` labels.
4. Show all years, including exact repeats.
5. Complete `second_pass_reviews[].synthesis_quality` only after separately confirming all five booleans: `problem_complete`, `explanation_complete`, `coherent_single_problem`, `coherent_single_answer`, and `format_complete`. A false or missing value blocks completion.

### Objective questions

- Use every distinct original choice from all linked occurrences.
- Retain original choice wording as separate original spans.
- Do not force four or five choices.
- Give each choice a verdict and explicit reason.
- Explain why wrong choices are wrong, not only why the answer is right.
- Map every source stem, condition, qualifier, number, choice, and problem-linked image finding to the completed problem.
- Merge semantically duplicate choices once with every source retained in the ledger. Preserve differences in condition, scope, exception, or detail.

### Essay questions

- Combine every distinct subquestion into a complete prompt.
- Build a complete answer containing all original explanation points.
- Add lecture-note scoring points only with `[족보 보충]`.
- Identify required keywords, sequence, comparisons, and common traps.

### Fragments

When a full problem cannot be safely reconstructed, create a keyword representative type. Keep the fragment unchanged and state exactly what is missing. Do not fabricate syntax or choices.

## Explanation completion

Create one logical and systematic complete answer that absorbs all required source meanings. Do not summarize, excerpt, concatenate source blocks, or organize the answer source by source.

The answer must read as one expert-authored solution, not as notes about the sources. Never write phrases such as `해설 참조`, narrate that a file was read, list citations in place of reasoning, or pad gaps with generic advice. For more than one linked occurrence, include an integrated solution component whose reconstruction provenance spans every linked question. Then organize the visible explanation by answer, reasoning, choice verdicts or scoring elements, related concepts and exceptions, and memorization points where supported.

Use sources in this order:

1. Original question-bank explanations.
2. Other original explanations linked to the same representative type.
3. Non-question lecture-note content with `[족보 보충 · file · page]`.
4. Verified authoritative external sources with `[AI 외부 보충 · source]`.
5. `[출처 확인 필요]` if no trustworthy basis exists.

External supplementation fills only a necessary gap after the supplied corpus is exhausted. Do not expand the answer into unrelated encyclopedic material.

## Double-pass completeness audit

Pass 1 atomizes sources, synthesizes the problem and answer, and maps every required atom to an internal output component ID. Pass 2 independently rereads the normalized source pages and searches for omitted choices, subquestions, meanings, qualifiers, conditions, exceptions, numbers, image findings, and conflicts.

Any new meaning found in Pass 2 becomes an atom and must be mapped. An unmapped atom, pending relevance decision, hidden conflict, incomplete reread, unreadable page/image, or unverifiable required supplement blocks `complete`.

If an original answer appears wrong, preserve it and add a separate sourced correction proposal. If sources disagree, present the disagreement and keep the run review-required.

## Images

- Use original question-bank images with `[원문]`; keep the image ID only in the ledger and non-visible DOCX metadata.
- Use a relevant lecture-note image only when its connection is supported; label it `[족보 보충]`.
- Keep uncertain images as whole-page evidence in the audit.
- Never regenerate a missing diagnostic or exam image and present it as original.

## Output contract

For each lecture unit and representative type, output the representative problem, complete sourced explanation, related images, every linked occurrence ordered by year and source order, every original answer/explanation, and separate reconstruction/correction/supplement blocks.

Do not compress, summarize away, or omit source occurrences to control document length.
