# Codebook — Advocacy Channels

*4,477 rows across 5 file(s). Generated 2026-08-07.*

Variables marked **internal** are retained for auditing and are not included in published extracts.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `oira_meeting_id` | text | code | 100% | Cedar-internal identifier for one OIRA EO 12866 meeting, built from the reginfo.gov meetingId. One row per meeting. |
| `channel` | text | code | 100% | Which advocacy channel the record comes from, from cedar_domain.AdvocacyChannel. Channels are never totalled together: a consultation is a statutory government-to-government obligation and an OIRA meeting is a regulatory-review request, neither of which is an LDA filing. |
| `meeting_date` | text | YYYY-MM-DD | 100% | Date of the OIRA meeting as reginfo.gov states it. |
| `rin` | text | code | 100% | Regulation Identifier Number of the rule under review, as printed on the meeting record. The join key to federal_actions.csv. |
| `rule_title` | text | text | 100% | Title of the rule under OIRA review, verbatim from the meeting record. |
| `agency` | text | text | 100% | Agency and sub-agency owning the rule, in reginfo's own `code-AGENCY/SUBAGENCY` form. |
| `requesting_organization` | text | text | 100% | The organisation named in reginfo's Requestor field, verbatim. Only the requester appears here; organisations that merely attended are recorded at their own grain in oira_meeting_participants.csv. |
| `entity_id` | text | code | 49% | Cedar entity the ORGANISATION resolved to. Blank where no guarded match was reached - which is not a statement that the organisation is not Native. A person is never resolved: attendee and witness names stay strings. |
| `attendees_external` | text | text | 100% | Non-government attendees as `Name (Affiliation)`, pipe-separated, verbatim from the meeting record. Names are strings: a person is never resolved to an entity. |
| `attendees_government` | text | text | 100% | Attendees whose stated affiliation is a government body - OMB/OIRA and the rulemaking agency - as `Name (Affiliation)`, pipe-separated. |
| `materials_submitted` | text | text | 54% | Titles of documents the requester lodged with OIRA, pipe-separated. |
| `materials_url` | text | URL | 54% | Download links for those documents on reginfo.gov, pipe-separated. |
| `source_url` | text | URL | 100% | Link to the record's published source. |
| `source_quote` | text | text | 100% | Verbatim text from the retrieved record that supports the row - the Requestor and attendee lines from reginfo, the witness line from Congress.gov or from the GPO MODS record. Whitespace is collapsed and long quotes are truncated; no word is changed. |
| `fetched_date` | text | YYYY-MM-DD | 100% | Date. |
| `tier` | text | code | 100% | A/B/C from cedar_domain.Tier. Tier A needs two legs, a name and an agreeing published state; reginfo and Congress.gov publish no state for an organisation, so their matches are Tier B pending a human ruling. C is unattributed. |
| `confidence` | numeric | 0.65 to 0.95 | 49% | One of: `0.75`, `0.90`, `0.65`, `0.85`, `0.95` |
| `built_date` | text | YYYY-MM-DD | 100% | Date. |
| `organization_class` | text | code | 100% | What was found about the organisation: NATIVE_ENTITY_SPINE (resolved to a Cedar entity), UNRESOLVED_NATIVE_MARKER (the name carries a Native marker word but no guarded match was reached), UNRESOLVED_NO_NATIVE_MARKER (not resolved, and the name carries no marker), GOVERNMENT (the other side of the table), UNCLASSIFIED (no organisation named). There is deliberately no NON_NATIVE value: failing to match is not evidence of not being Native, and asserting otherwise would be an authored characterisation of a named party. |
| `resolution_basis` | text | code | 100% | How the organisation was resolved, or why it was refused. Matches carry the resolve_entity tier - exact, alias, core, or containment_within_official_name - suffixed `_name_only` where only the name supports it or `_plus_state` where a published state also agrees. Refusals name the guard that fired: refused_specificity, refused_containment_uncorroborated, refused_state_disagreement, refused_trap_tokens, refused_single_token_uncorroborated, refused_missing_native_identity_word, refused_corporate_form_vs_government, no_spine_match, government_body. |
| `native_slice_basis` | text | code | 100% | Why this row is in the published Native slice rather than only in the retained corpus: REQUESTOR_RESOLVED, REQUESTOR_NATIVE_MARKER, ATTENDEE_RESOLVED, ATTENDEE_NATIVE_MARKER, WITNESS_ORG_RESOLVED, WITNESS_ORG_NATIVE_MARKER. |
| `hearing_appearance_id` | text | code | 100% | Cedar-internal identifier for one witness appearing at one congressional committee meeting. Built from congress, chamber, the Congress.gov eventId and the witness's position in the witness list. |
| `congress` | integer | integer | 98% | Number of the Congress in which the hearing was held. |
| `chamber` | text | category | 100% | House, Senate or Joint. |
| `committee` | text | text | 98% | Parent committee, from the Congress.gov committee name with any `Subcommittee on ...` clause removed. |
| `subcommittee` | text | text | 38% | Subcommittee clause of the Congress.gov committee name, blank where the full committee met. |
| `hearing_title` | text | text | 100% | Title of the committee meeting, verbatim from Congress.gov. |
| `hearing_date` | text | YYYY-MM-DD | 100% | Date of the committee meeting. |
| `witness_name` | text | text | 100% | The witness's name as Congress.gov prints it, honorific included. A string, never an entity. |
| `witness_title` | text | text | 94% | The witness's stated position or title. |
| `witness_organization` | text | text | 100% | The organisation the witness is listed as representing. This is the party that is resolved through the spine. |
| `testimony_url` | text | URL | 38% | The witness's own prepared-statement PDF on congress.gov, matched on the surname token in the filename. Blank where no statement was posted. |
| `is_written_only` | text | true/blank | 0% | `true` only where the record itself says the submission was written or for the record. Blank means the source does not say - it is never inferred from the absence of a transcript. |
| `oira_participant_id` | text | code | 100% | Cedar-internal identifier for one named person at one OIRA meeting. |
| `participant_name` | text | text | 100% | The attendee's name exactly as the meeting record prints it. A string: a person is never resolved to an entity. |
| `participant_organization` | text | text | 100% | The affiliation the attendee gave. This is the party that is resolved through the spine. |
| `side` | text | code | 100% | EXTERNAL for an outside party, GOVERNMENT for OMB/OIRA and the rulemaking agency. Derived from the agency acronyms reginfo itself uses on the meeting records. |
| `is_requestor_organization` | integer | 0/1 | 100% | 1 where this attendee's affiliation is the organisation named in the meeting's Requestor field. |
| `participation_mode` | text | category | 100% | How the attendee took part, as the record states it - in person, teleconference. |
| `federal_action_document_number` | text | code | 100% | Federal Register document number of the action sharing this RIN. |
| `federal_action_publication_date` | text | YYYY-MM-DD | 100% | Publication date of that Federal Register action. |
| `federal_action_type` | text | category | 100% | Federal Register document type of that action. |
| `federal_action_title` | text | text | 100% | Title of that Federal Register action, truncated. |
| `link_basis` | text | code | 100% | What the link rests on: `rin_exact` for a meeting matched to a Federal Register action on an identical RIN, `congress_gov_related_item` for a bill Congress.gov itself lists as the meeting's related item. |
| `relationship` | text | code | 100% | What the link file asserts. Both values state co-occurrence only: an OIRA meeting and a rule, or a hearing and a bill, are recorded with their dates. Cedar never asserts that advocacy caused an outcome. |
| `event_id` | integer | code | 100% | Congress.gov committee-meeting event identifier. |
| `meeting_type` | text | category | 100% | Congress.gov meeting type - Hearing, Meeting, Markup. |
| `has_witness_appearances` | integer | 0/1 | 100% | 1 where the linked committee meeting also produced witness rows. Markups have no witnesses, which is why bill links are not restricted to meetings that do. |
| `bill_id` | text | code | 100% | Identifier. |
| `bill_title` | text | text | 100% | Descriptive name. |
| `bill_introduced_date` | text | YYYY-MM-DD | 100% | Date the linked bill was introduced. |

## Value sets

- **`channel`** — `HEARING_TESTIMONY`, `OIRA_MEETING`
- **`agency`** — `1024-DOI/NPS`, `2120-DOT/FAA`, `2060-EPA/OAR`, `1076-DOI/BIA`, `1004-DOI/BLM`, `0596-USDA/FS`, `1240-DOL/OWCP`, `0648-DOC/NOAA`, `0579-USDA/APHIS`, `0910-HHS/FDA`, `0331-CEQ`, `2008-EPA/RODENVER`, `0991-HHS/OS`, `1029-DOI/OSMRE`, `1870-ED/OCR`, `0970-HHS/ACF`, `2127-DOT/NHTSA`, `2040-EPA/OW`, `1006-DOI/RB`, `2050-EPA/SWER`, `2070-EPA/OCSPP`, `3245-SBA`, `2060-EPA/AR`, `0710-DOD/COE`, `2501-HUD/HUDSEC`
- **`tier`** — `C`, `B`, `A`
- **`organization_class`** — `NATIVE_ENTITY_SPINE`, `UNRESOLVED_NATIVE_MARKER`, `GOVERNMENT`, `UNRESOLVED_NO_NATIVE_MARKER`
- **`native_slice_basis`** — `WITNESS_ORG_RESOLVED`, `WITNESS_ORG_NATIVE_MARKER`, `ATTENDEE_NATIVE_MARKER`, `REQUESTOR_RESOLVED`, `ATTENDEE_RESOLVED`, `REQUESTOR_NATIVE_MARKER`
- **`chamber`** — `House`, `Senate`, `Joint`
- **`side`** — `GOVERNMENT`, `EXTERNAL`
- **`participation_mode`** — `Teleconference`, `In Person`, `Did Not Attend`
- **`federal_action_type`** — `Proposed Rule`, `Rule`, `Notice`
- **`link_basis`** — `congress_gov_related_item`, `rin_exact`
- **`relationship`** — `hearing_concerns_bill`, `co_occurrence_meeting_and_rule`
- **`meeting_type`** — `Meeting`, `Markup`, `Hearing`, `Open Business Meeting`, `Open Hearing`
