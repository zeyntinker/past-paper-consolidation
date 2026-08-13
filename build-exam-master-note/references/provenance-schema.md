# Provenance and ledger schema

## Core records

Store the run ledger as UTF-8 JSON with `schema_version: 2`. Use stable string IDs. IDs are internal audit keys and must not appear in visible study content.

### `source_artifacts[]`

Require `id`, `logical_artifact_id`, `file_name`, `format`, `sha256`, `size_bytes`, `source_role`, `source_link_index`, `page_count`, `processed_pages`, and `status`. `processed_pages` must equal every physical page number from 1 through `page_count` before completion.

### `question_occurrences[]`

Each occurrence is immutable and separate, even when identical to another year. Require:

- `id`, `source_artifact_id`, `year`, `source_order`, and `source_page`
- `question_type`
- `original_problem`
- `original_choices` (list; empty when not applicable)
- `original_answer` and `original_explanation`
- `image_ids`
- exactly one of `representative_type_id` or `review_queue_id`
- `word_location` and `status`

Store missing source fields as empty strings, not invented text. Preserve newlines and typos.

### `images[]`

Require `id`, `source_artifact_id`, `source_page`, `path`, `question_ids`, `provenance`, `word_location`, and `status`.

### `representative_types[]`

Require `id`, `title`, `question_type`, `lecture_unit`, `question_ids`, `problem_components`, `choice_components`, `answer_components`, and `explanation_components`.

Every component contains an internal `id`, `text`, and `provenance[]`. Choice components additionally contain `verdict` and `rationale_components`; every rationale also has an internal component ID.

### `semantic_atoms[]`

Create atoms before synthesis. Each atom is the smallest independently checkable source meaning or image finding. Require:

- `id` and `representative_type_id`;
- `category`: `problem`, `original_explanation`, `lecture_note`, or `external_supplement`;
- a narrow `atom_type`, such as stem, condition, choice, subquestion, answer, rationale, definition, mechanism, finding, image, criterion, differential, treatment, indication, contraindication, prognosis, exception, trap, or prerequisite;
- `source_artifact_id`, `source_page`, and exact source `text` or `image_id`;
- `source_question_id` and `source_field` when the atom comes from a question occurrence;
- `choice_index` when `source_field` is `original_choices`;
- `provenance_kind`, `relevance_status`, and `status`;
- optional `duplicate_group_id` or `conflict_group_id`.

Use `relevance_status` values `required`, `excluded`, or `review_required`. An excluded lecture-note atom requires a written `exclusion_reason`. Ambiguous relevance stays `review_required` and blocks completion.

An `external_supplement` atom uses `provenance_kind: external_ai_supplement` and requires a human-readable `citation` plus stable `locator` instead of a OneDrive artifact/page. It must fill a specific required gap and map to the answer side.

### `semantic_coverage[]`

Require `id`, `atom_id`, `representative_type_id`, `target_kind`, `target_component_ids`, `integration_mode`, and `status`.

- Problem atoms target only problem or choice components.
- Original-explanation and lecture-note atoms target only answer, rationale, or explanation components.
- Use integration modes `exact`, `synthesized`, `duplicate_merged`, or `conditional_split`.
- Every required atom has exactly one coverage record. A record may point to multiple output components.
- Duplicate atoms may share one target component only when each atom retains its own mapping and uses `duplicate_merged`.
- Conflicting conditions must use `conditional_split` and target distinct visible components. Unresolved conflicts block completion.

### `second_pass_reviews[]`

Require one record per representative type with `id`, `representative_type_id`, `reviewed_sources`, `discovered_atom_ids`, `unresolved_atom_ids`, `notes`, and `status`.

`reviewed_sources` lists every independently reread source artifact and physical page. It must cover all linked question pages and every required or review-pending atom page. Newly discovered meanings become atoms and must be mapped. Completion requires `status: complete` and an empty `unresolved_atom_ids` list.

### `prior_year_sequence[]`

Require `sequence`, `question_ids`, `reconstruction_source_ids`, `explanation_source_ids`, `conflict_status`, and `supplement_components`.

### `audit_findings[]`

Require `id`, `severity` (`blocking`, `warning`, or `info`), `code`, `message`, `source_locations`, and `status`.

## Provenance labels

Use `kind` values:

- `original`
- `ai_reconstruction_from_questions`
- `lecture_note_supplement`
- `master_note_supplement`
- `external_ai_supplement`
- `source_unverified`

An `original` span must include `source_question_id` and `source_field`. Its text must equal that source field exactly. Original images cite `source_image_id`.

Lecture-note supplements require `source_artifact_id` and `source_page`. Master-note supplements require `representative_type_id`. External supplements require a human-readable citation and a stable URL, ISBN/page, DOI, or official publication identifier.

## Immutable-original rules

1. Do not normalize spelling, punctuation, spacing, or terminology in an original span.
2. Do not replace a wrong answer. Add a separate correction component.
3. Do not collapse identical occurrences across years.
4. Do not use one occurrence as a substitute for a missing occurrence.
5. Do not attach an image to a question when the relation is uncertain; retain it as review-required page evidence.

## Representative-type rules

- A representative type is synthetic and never replaces source occurrences.
- Objective types contain the union of all non-duplicate original choices.
- Do not invent choices to reach a conventional choice count.
- Each choice has a verdict and sourced rationale.
- Essay types cover every distinct subquestion and scoring point found in linked occurrences and relevant lecture-note material.

## Required relationships

- `manifest_fingerprint` must equal `approved_manifest_fingerprint`.
- Every included source artifact has normalized output or a blocking finding.
- Every source page has a processed status.
- Every question occurrence maps to exactly one representative type or review queue.
- Every question occurrence has a Word location before completion.
- Every image has a Word location or a blocking review finding.
- Every representative component has at least one provenance record.
- Every representative has required problem atoms and required explanation atoms.
- Every linked nonempty original problem, choice, answer, and explanation field contributes at least one required atom; every choice is indexed separately.
- Every required atom maps to the correct side of the same representative.
- Every representative has one complete second-pass source reread covering all applicable source pages.
- File counts and visible substring checks never substitute for semantic coverage.
