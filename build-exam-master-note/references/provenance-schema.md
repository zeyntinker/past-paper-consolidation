# Provenance and ledger schema

## Core records

Store the run ledger as UTF-8 JSON. Use stable string IDs.

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

Require `id`, `title`, `question_type`, `lecture_unit`, `question_ids`, `problem_components`, `choice_components`, and `explanation_components`.

Every component contains `text` and `provenance[]`. Choice components additionally contain `verdict` and `rationale_components`.

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
