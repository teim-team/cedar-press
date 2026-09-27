/** Source observations for an exact enterprise, never an affiliated tribe. */
export const NEED_EVIDENCE_EMPTY = "No released patent or rating evidence is connected to this profile yet. This does not establish that none exists.";

export function isEnterpriseSubject(id) {
  return typeof id === "string" && /^(?:CEDAR-NEST-|CB-)[A-Za-z0-9-]+$/.test(id);
}

function sourceLink(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}

export function evidenceSections(profile) {
  if (profile?.status !== "available") return [];
  const rows = (key) => (Array.isArray(profile[key]) ? profile[key] : [])
    .filter((row) => row.publication_status === "eligible" && !row.hold_reason && sourceLink(row.source_url));
  return [
    { title: "Patent observations", items: rows("patent_observations").map((row) => ({
      id: row.observation_id,
      label: [row.subject_name, row.patent_number || row.publication_id, row.relationship_type].filter(Boolean).join(" · "),
      detail: [row.title, row.event_date || row.grant_date || "Date not established",
        row.family_id && `Family: ${row.family_id}`, row.original_assignee && `Original assignee: ${row.original_assignee}`,
        row.subsequent_owner && `Subsequent owner: ${row.subsequent_owner}`,
        row.assignment_date && `Assignment: ${row.assignment_date}`, row.acquisition_date && `Acquisition: ${row.acquisition_date}`,
        "Current patent ownership is not established by an acquisition alone."].filter(Boolean).join(" — "),
      source: sourceLink(row.source_url),
    })) },
    { title: "Credit rating history", items: rows("credit_rating_actions").map((row) => ({
      id: row.observation_id,
      label: [row.issuer_name, row.agency, row.rating, row.action].filter(Boolean).join(" · "),
      detail: [row.instrument || row.rating_scope, row.action_date || row.publication_date || "Date not established",
        row.outlook && `Outlook: ${row.outlook}`, row.watch && `Watch: ${row.watch}`,
        (row.preliminary === true || row.preliminary === "true") && "Preliminary",
        (row.expected === true || row.expected === "true") && "Expected",
        "Historical observation; not a verified current rating."].filter(Boolean).join(" — "),
      source: sourceLink(row.source_url),
    })) },
    { title: "Rating availability", items: rows("rating_availability").map((row) => ({
      id: row.availability_id,
      label: [row.subject_name, row.agency, row.availability_status].filter(Boolean).join(" · "),
      detail: [row.publication_period, row.rating_scope, "Availability is not a rating grade."].filter(Boolean).join(" — "),
      source: sourceLink(row.source_url),
    })) },
  ].filter((section) => section.items.length);
}
