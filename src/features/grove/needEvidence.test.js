import assert from "node:assert/strict";
import test from "node:test";
import { attributionLabel, evidenceSections, NEED_EVIDENCE_EMPTY } from "./needEvidence.js";

test("An empty NEED profile does not claim absence of underlying facts", () => {
  assert.match(NEED_EVIDENCE_EMPTY, /does not establish/);
  assert.match(attributionLabel({ profile_attribution: { kind: "registered_entity" } }), /this registered entity/);
  assert.match(attributionLabel({ profile_attribution: { kind: "related_enterprise" } }), /not assigned to the profile entity/);
});

test("Held, missing and unsafe-source facts never become visible evidence", () => {
  const row = { publication_status: "eligible", source_url: "https://example.org", hold_reason: "" };
  assert.deepEqual(evidenceSections({ status: "publication_held", patent_observations: [row] }), []);
  assert.deepEqual(evidenceSections(null), []);
  assert.deepEqual(evidenceSections({ status: "available", patent_observations: [
    { ...row, hold_reason: "rights" }, { ...row, publication_status: "held" },
    { ...row, source_url: "javascript:alert(1)" }, { ...row, source_url: "https://u:p@example.org" },
    { ...row, source_url: "invalid" },
    { ...row, source_url: "https://example.org/report?token=synthetic" },
    { ...row, source_url: "https://host.internal/report" },
  ] }), []);
});

test("Issuer, instrument, historical status and patent assignment caution remain visible", () => {
  const row = { publication_status: "eligible", source_url: "https://example.org", hold_reason: "" };
  const sections = evidenceSections({ status: "available",
    patent_observations: [{ ...row, observation_id: "p", subject_name: "Enterprise A", publication_id: "SYNTH", relationship_type: "grant" }],
    credit_rating_actions: [{ ...row, observation_id: "r", issuer_name: "Enterprise B", agency: "Agency", rating: "BBB-", instrument: "Secured notes", action: "Withdrawn", outlook: "Negative" }],
    rating_availability: [{ ...row, availability_id: "a", subject_name: "Enterprise C", agency: "Agency", availability_status: "not_rated" }],
  });
  assert.equal(sections.length, 3);
  assert.match(sections[0].items[0].detail, /ownership is not established/);
  assert.match(sections[1].items[0].label, /Enterprise B.*BBB-.*Withdrawn/);
  assert.match(sections[1].items[0].detail, /Secured notes.*Negative.*not a verified current/);
  assert.match(sections[2].items[0].detail, /not a rating grade/);
});

test("Patent recordation never substitutes for the ownership effective date", () => {
  const sections = evidenceSections({ status: "available", patent_events: [{
    event_id: "synthetic-event", subject_name: "Synthetic subsidiary", patent_number: "SYNTH",
    event_type: "assignment_recorded", effective_date: "2018-05-01", recordation_date: "2025-02-01",
    source_url: "https://example.org/evidence", publication_status: "eligible", hold_reason: "",
  }] });
  assert.equal(sections.length, 1);
  assert.match(sections[0].items[0].detail, /Effective date: 2018-05-01; Recorded: 2025-02-01/);
  assert.match(sections[0].items[0].detail, /do not alone establish current ownership/);
});
