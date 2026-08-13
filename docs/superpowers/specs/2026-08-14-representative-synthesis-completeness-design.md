# Representative Synthesis and Semantic Completeness Design

## Objective

Strengthen the exam master-note skill so that each representative problem and its explanation become one coherent, complete study unit while every source meaning remains auditable. Completeness must cover both the representative problem and the representative explanation, not merely the presence of source files or year-specific originals.

The learning DOCX must remain readable. Internal representative, question, and source-atom IDs belong in the machine ledger and must not appear in visible study content.

## Non-negotiable preservation rules

- Preserve every year-specific original problem and original explanation exactly, even when incomplete, malformed, questionable, or repeated in another year.
- Never replace year-specific originals with the representative synthesis.
- Never silently correct an original. Put verification or supplementation beside it with the appropriate provenance.
- A representative problem must not introduce a tested point unsupported by the supplied sources.
- A representative explanation must not summarize away a definition, condition, mechanism, finding, criterion, image point, differential, treatment point, indication, contraindication, prognosis point, exception, trap, prerequisite concept, choice rationale, or scoring point that is relevant to answering the problem.
- Any unreviewed ambiguity, unresolved conflict, or unmapped required source meaning blocks `complete` status.

## Source scope and precedence

For the lecture-order master note, use the problem bank and lecture notes available through the user's first link. For the previous-year practical-order section, treat the previous-year reconstruction and explanation files found through the user's second link as the originals.

Use evidence in this order:

1. Original problem-bank or previous-year reconstruction text and images.
2. Relevant explanations included in those files.
3. Relevant lecture-note text and images from the first-link corpus.
4. External authoritative sources only when the supplied corpus cannot fill a required gap.

External material must fill a specific gap only. It must not expand the answer into unrelated encyclopedic content.

## Semantic source atoms

Before synthesis, split the source material into the smallest independently checkable meanings, called source atoms. Atom IDs are internal ledger keys only.

### Problem atoms

Capture every source element that constrains what is being asked:

- stem facts and conditions;
- every distinct objective choice;
- every essay or short-answer subquestion;
- numbers, units, qualifiers, negations, and answer formats;
- problem-linked tables, figures, labels, and image findings;
- source wording fragments whose intended question can be reconstructed without inventing a new tested point.

### Explanation atoms

Capture every meaning contained in the original explanations, including conclusions, rationales, caveats, exceptions, and contradictions. An incorrect or doubtful original explanation is still preserved as an original atom and separately flagged for verification.

### Relevant lecture-note atoms

Capture all lecture-note content needed to understand, derive, justify, or safely qualify the answer, including:

- definitions and prerequisite concepts;
- causes, mechanisms, and pathophysiology;
- symptoms, signs, findings, tests, images, and diagnostic criteria;
- differential diagnosis and distinguishing features;
- treatment, indications, contraindications, and prognosis;
- exceptions, traps, and course-specific emphasis.

Material is relevant when it supports a problem atom, explanation atom, answer rationale, or a necessary exception. Mere proximity in the same lecture is not enough. Ambiguous relevance is retained as a review candidate and blocks `complete` until resolved.

## Representative problem synthesis

Create one polished problem for each representative type. It is a reconstruction, not a list of originals.

- Combine the supported testing intent into one natural stem.
- Reorder wording and conditions when needed for clarity, while preserving meaning.
- For objective questions, include every distinct source choice. Semantically duplicate choices may be merged once, but all supporting sources remain mapped in the ledger.
- For essay questions, combine all supported subquestions in a logical order.
- For fragmentary reconstructions, complete only the wording required to express the supported intent. Do not invent a new fact, choice, subquestion, or tested point.
- When sources conflict because they describe different conditions, split the representative problem into explicit conditional subquestions or choices where the evidence supports that distinction.
- When a conflict cannot be resolved safely, expose it as review-required instead of forcing a single formulation.

The representative problem is complete only when every required problem atom maps to a visible component of the synthesized problem.

## Representative explanation synthesis

Create one logical, systematic, complete answer. Do not concatenate quotations, present a source-by-source digest, or shorten it into a key-point summary.

Organize the answer according to the question type and subject matter. The default structure is:

1. Direct answer or conclusion.
2. Choice-by-choice rationale or subquestion-by-subquestion answer.
3. Full conceptual basis and mechanism.
4. Diagnostic, imaging, differential, treatment, and prognostic details when relevant.
5. Conditions, exceptions, contradictions, and exam traps.

Every distinct meaning from all original problem-bank explanations and every relevant lecture-note atom must be absorbed into this answer. Duplicate meanings should appear once in the prose, with all supporting sources linked internally. Differences in condition, exception, scope, or detail must remain explicit rather than being collapsed as duplicates.

For objective questions, state the correct answer and give the true/false judgment and complete basis for every distinct choice. For essay questions, provide a coherent model answer containing every supported scoring point. For short-answer questions, state the answer clearly and then provide its complete basis.

When supplied evidence is insufficient, add only the necessary external supplementation and label it visibly as `[AI 외부 보충 · source]`. Unverifiable content is labeled `[출처 확인 필요]` and blocks `complete`.

## Double-pass completeness audit

Completeness is established with two independent passes.

### Pass 1: extraction and synthesis mapping

1. Atomize all problem elements, original explanation meanings, and relevant lecture-note meanings.
2. Synthesize the representative problem and representative explanation.
3. Map every problem atom to a representative-problem component.
4. Map every explanation and relevant lecture-note atom to a representative-explanation component.
5. Record merged duplicates as multiple source atoms supporting one output component.

### Pass 2: independent source reread

Reread the normalized source independently of the first extraction and compare it against both atom inventories and synthesized outputs. Search specifically for omitted meanings, choices, subquestions, qualifiers, conditions, exceptions, numbers, image findings, and conflicts.

Any newly found element is added to the atom inventory and mapped before completion. The validator must fail closed when:

- a required problem atom is unmapped;
- an explanation or relevant lecture-note atom is unmapped;
- an atom maps only to a year-specific original but not to the applicable representative output;
- a relevance decision is still pending;
- a source conflict is hidden or unresolved;
- required external supplementation lacks a usable source;
- source text or an image cannot be inspected reliably.

File counts, question counts, or substring presence alone are not proof of semantic completeness.

## Provenance shown to the learner

Use plain bracketed text only; do not use colored badges. Display human-readable provenance immediately beside or below the supported content. Examples:

- `[원문 · 2024 기출.pdf · 12쪽]`
- `[기출 통합 재구성 · 2022년·2024년 기출 참고]`
- `[족보 참고 · 강의정리.pdf · 31쪽]`
- `[AI 외부 보충 · source]`
- `[출처 확인 필요]`

Do not visibly print representative IDs, question IDs, atom IDs, database keys, or similar technical identifiers in headings, tables, provenance, image captions, headers, or body text. Retain them in the ledger and, where deterministic verification needs them, in non-visible document metadata only.

Content copied unchanged from the applicable original receives `[원문]` provenance. Any reconstructed, merged, lecture-note-derived, or externally supplied span must use the corresponding non-original label; modified text must never be labeled `[원문]`.

## DOCX structure

Keep the established three-part order:

1. Lecture-order master note.
2. Previous-year exam in practical order.
3. Completeness audit.

Keep the established readable layout: A4 portrait, header-only navigation, no table of contents, 45:55 problem/explanation tables, and full-width related images. The representative table contains the synthesized problem and complete answer. Below it, every year-specific occurrence is repeated in its own table with its original problem and original explanation unchanged.

Part 3 is deliberately compact. For each representative item, show only:

- problem coverage;
- explanation coverage;
- unresolved-item count;
- status.

Show a short detail only for missing, conflicting, or review-required cases. Keep the full atom-to-output mappings in the machine ledger, not in the study DOCX.

## Ledger and validation requirements

The ledger must retain stable internal IDs and record:

- all problem, explanation, and relevant lecture-note atoms;
- source file, page, question or image relation, and original text or image reference;
- relevance status and reviewer decision;
- representative output component mappings;
- duplicate and conflict relationships;
- provenance category;
- pass-2 audit result;
- unresolved items and final status.

Automated validation must prove structural coverage from the ledger and fail on any missing mapping. It must also verify that the visible DOCX does not expose technical IDs, while confirming that human-readable provenance and the compact Part 3 status are present.

Deterministic validation cannot by itself prove that human atomization captured every meaning. Therefore `complete` requires both successful automated mapping checks and a recorded independent pass-2 source reread.

## Acceptance cases

Tests and fixtures must cover at least:

- a missing problem atom causes failure;
- a missing original-explanation atom causes failure;
- a missing relevant lecture-note atom causes failure;
- semantically duplicate atoms consolidate into one output component while retaining all source mappings;
- different conditions or exceptions remain separately represented;
- an unresolved conflict or ambiguous relevance decision blocks `complete`;
- every objective choice has a verdict and rationale;
- every essay subquestion and scoring point is represented;
- image-derived problem and explanation atoms are mapped and rendered;
- external supplementation is narrowly scoped and visibly labeled;
- year-specific originals remain unchanged and repeated across years;
- the DOCX contains no visible representative, question, or atom IDs;
- the ledger retains all internal IDs;
- Part 3 stays compact for passing items and expands only for exceptions.

## Implementation boundary

After this design is approved, prepare a separate implementation plan. Expected implementation areas are `SKILL.md`, the provenance and master-note protocol references, the ledger schema and validator, DOCX generation and verification, and pipeline tests. Do not weaken existing source selection, `합본` exclusion, PDF/HWP/HWPX handling, chronological and period ordering, image preservation, or fail-closed behavior.
