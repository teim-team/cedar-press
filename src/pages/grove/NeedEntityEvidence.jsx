import { useEffect, useState } from "react";

import { apiAvailable, getNeedEntityEvidence } from "../../api.js";
import { NEED_EVIDENCE_EMPTY, evidenceSections } from "../../features/grove/needEvidence.js";

export default function NeedEntityEvidence({ cedarUid }) {
  const [profile, setProfile] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    if (apiAvailable()) {
      getNeedEntityEvidence(cedarUid, { signal: controller.signal })
        .then((result) => { if (!controller.signal.aborted) setProfile({ ...result, subject: cedarUid }); })
        .catch(() => { if (!controller.signal.aborted) setProfile({ status: "unavailable", subject: cedarUid, message: "Verified NEED evidence is unavailable right now." }); });
    }
    return () => controller.abort();
  }, [cedarUid]);
  const current = profile?.subject === cedarUid ? profile : null;
  return (
    <section className="cp-rec__block" aria-label="NEED patent and rating evidence">
      <h2>Patents and credit ratings</h2>
      <p className="cp-rec__fine">{current?.message || NEED_EVIDENCE_EMPTY}</p>
      {current?.related_enterprises?.length ? (
        <div><h3>Related NEED enterprises</h3><ul>
          {current.related_enterprises.map((item) => (
            <li key={item.profile_link_id}>{item.enterprise_name} — {item.relationship_type}
              {item.valid_from || item.valid_to ? ` (${item.valid_from || "start unknown"} to ${item.valid_to || "end unknown"})` : " (relationship dates not established)"}
              {" "}<a href={item.source_url} target="_blank" rel="noopener noreferrer">Relationship source</a>
            </li>
          ))}
        </ul></div>
      ) : null}
      {evidenceSections(current).map((section) => (
        <div key={section.title}>
          <h3>{section.title}</h3>
          <ul>{section.items.map((item) => (
            <li key={item.id}>
              <strong>{item.label}</strong><p>{item.detail}</p>
              <a href={item.source} target="_blank" rel="noopener noreferrer">Source</a>
            </li>
          ))}</ul>
        </div>
      ))}
      {current?.release_id ? <p className="cp-rec__fine">Release: <code>{current.release_id}</code></p> : null}
    </section>
  );
}
