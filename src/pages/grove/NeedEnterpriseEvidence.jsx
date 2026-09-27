import { useEffect, useState } from "react";

import { apiAvailable, getNeedEnterpriseEvidence } from "../../api.js";
import { NEED_EVIDENCE_EMPTY, evidenceSections } from "../../features/grove/needEvidence.js";

export default function NeedEnterpriseEvidence({ enterpriseId }) {
  const [profile, setProfile] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    if (apiAvailable()) {
      getNeedEnterpriseEvidence(enterpriseId, { signal: controller.signal })
        .then((result) => { if (!controller.signal.aborted) setProfile({ ...result, subject: enterpriseId }); })
        .catch(() => { if (!controller.signal.aborted) setProfile({ status: "unavailable", subject: enterpriseId, message: "Verified enterprise evidence is unavailable right now." }); });
    }
    return () => controller.abort();
  }, [enterpriseId]);
  const current = profile?.subject === enterpriseId ? profile : null;
  return (
    <section className="cp-rec__block" aria-label="NEED patent and rating evidence">
      <h2>Patents and credit ratings</h2>
      <p className="cp-rec__fine">{current?.message || NEED_EVIDENCE_EMPTY}</p>
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
