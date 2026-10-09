/** Evidence retains its exact registered legal subject or related enterprise. */
import { safeSourceUrl } from "./sourcePresentation.js";
export const NEED_EVIDENCE_EMPTY = "No released patent or rating evidence is connected to this profile yet. This does not establish that none exists.";

function sourceLink(value) {
  const safe = safeSourceUrl(value);
  return safe?.startsWith("https://") ? safe : null;
}

export function attributionLabel(row) {
  return row.profile_attribution?.kind === "registered_entity"
    ? "Legal subject: this registered entity"
    : "Legal subject: the named related enterprise; this fact is not assigned to the profile entity";
}

export function evidenceSections(profile) {
  if (profile?.status !== "available") return [];
  const rows = (key) => (Array.isArray(profile[key]) ? profile[key] : [])
    .filter((row) => row.publication_status === "eligible" && !row.hold_reason && sourceLink(row.source_url));
  return [
    { title: "Patent observations", items: rows("patent_observations").map((row) => ({
      id: row.observation_id,
      label: [row.subject_name, row.patent_number || row.publication_id, row.relationship_type].filter(Boolean).join(" · "),
      detail: [attributionLabel(row), row.title, row.event_date || row.grant_date || "Date not established",
        row.family_id && `Family: ${row.family_id}`, row.original_assignee && `Original assignee: ${row.original_assignee}`,
        row.subsequent_owner && `Subsequent owner: ${row.subsequent_owner}`,
        row.assignment_date && `Assignment: ${row.assignment_date}`, row.acquisition_date && `Acquisition: ${row.acquisition_date}`,
        "Current patent ownership is not established by an acquisition alone."].filter(Boolean).join(" · "),
      source: sourceLink(row.source_url),
    })) },
    { title: "Patent events", items: rows("patent_events").map((row) => ({
      id: row.event_id,
      label: [row.subject_name, row.patent_number || row.publication_id, row.event_type].filter(Boolean).join(" · "),
      detail: [attributionLabel(row),
        `Effective date: ${row.effective_date || "not established"}`,
        `Recorded: ${row.recordation_date || "not established"}`,
        row.from_party && `From: ${row.from_party}`, row.to_party && `To: ${row.to_party}`,
        row.review_note,
        "Recordation, security interests and fee events do not alone establish current ownership."
      ].filter(Boolean).join("; "),
      source: sourceLink(row.source_url),
    })) },
    { title: "Credit rating history", items: rows("credit_rating_actions").map((row) => ({
      id: row.observation_id,
      label: [row.issuer_name, row.agency, row.rating, row.action].filter(Boolean).join(" · "),
      detail: [attributionLabel(row), row.instrument || row.rating_scope,
        row.rating_type && `Rating type: ${row.rating_type}`,
        `Action date: ${row.action_date || "not established"}`,
        row.publication_date && `Published: ${row.publication_date}`,
        row.observation_as_of && `Observed: ${row.observation_as_of}`,
        row.outlook && `Outlook: ${row.outlook}`, row.watch && `Watch: ${row.watch}`,
        (row.preliminary === true || row.preliminary === "true") && "Preliminary",
        (row.expected === true || row.expected === "true") && "Expected",
        "Historical observation; not a verified current rating."].filter(Boolean).join(" · "),
      source: sourceLink(row.source_url),
    })) },
    { title: "Rating availability", items: rows("rating_availability").map((row) => ({
      id: row.availability_id,
      label: [row.subject_name, row.agency, row.availability_status].filter(Boolean).join(" · "),
      detail: [attributionLabel(row), row.publication_period, row.rating_scope, "Availability is not a rating grade."].filter(Boolean).join(" · "),
      source: sourceLink(row.source_url),
    })) },
  ].filter((section) => section.items.length);
}
