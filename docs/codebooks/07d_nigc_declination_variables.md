# Codebook - NIGC declination layer

*Variables only. Written by `code/100_finish_declinations_and_employment.py`.*

## Variables added 2026-08-07 (script 100)

### `nigc_declination_letters.csv`

| variable | type | definition |
|---|---|---|
| `evidentiary_stage` | enum | Always `NIGC_REVIEWED` on a letter. The letter proves review of submitted unexecuted documents and nothing further. |
| `evidentiary_ladder` | string | `NIGC_REVIEWED -> EXECUTION_UNCONFIRMED -> EXECUTED_CONFIRMED -> CLOSED_CONFIRMED -> SUPERSEDED / TERMINATED` |
| `evidentiary_stage_basis` | string | The agency's own sentence supporting the stage. |
| `what_this_does_not_establish` | string | Execution, closing, construction, opening, continued operation, land status, gaming eligibility. |
| `what_would_advance_the_stage` | string | The document class that would move the row to the next rung. |
| `text_recovery_status` | enum | `ocr_recovered`, `ocr_returned_too_little_text`, or blank where a publisher text layer existed. |
| `ocr_engine` / `ocr_dpi` / `ocr_date` | string | Provenance of the recovered text. |
| `ocr_text_chars` / `ocr_common_word_ratio` | integer / float | Volume and plausibility of the recovered text. |
| `finding_evidence_basis` | enum | `OCR_RECOVERED` where the finding was read from OCR rather than a text layer. |
| `ocr_caution` | string | Why an OCR-derived finding is weaker: a negation eaten by OCR inverts the finding. |

### `gaming_financing_events.csv`

| variable | type | definition |
|---|---|---|
| `evidentiary_stage` | enum | Always `EXECUTION_UNCONFIRMED`. |
| `evidentiary_ladder` | string | As above. |
| `evidentiary_stage_basis` | string | Why the event is evidenced but its execution is not. |
| `property_attachment_caution` | string | A financing is never attached to a property because the enterprise owns it. |
| `text_basis` | enum | `OCR_RECOVERED` on events derived from a recovered image-only letter. |

### `gaming_source_claims.csv`

| variable | type | definition |
|---|---|---|
| `evidentiary_stage` | enum | Always `NIGC_REVIEWED`. |
| `evidentiary_ladder` | string | As above. |
| `claim_scope_caution` | string | Tribe, gaming authority, gaming enterprise, property-owning subsidiary and operating company are five different legal persons. |
