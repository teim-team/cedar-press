// REVIEW OWNER: Havala
//
// "How to read these records" for the collections whose columns need a key
// (NEED and PLOT, readingKeys.js). Closed by default: the records come first,
// and the key is one click away for a reader who meets "subsidiary_of" or
// "BIA tract" for the first time.

import { readingKey } from "../../features/grove/readingKeys.js";

export default function PressReadingKey({ collectionId }) {
  const key = readingKey(collectionId);
  if (!key) return null;
  return (
    <details className="cp-key" data-testid="reading-key">
      <summary>How to read these records</summary>
      <div className="cp-key__in">
        <p className="cp-key__intro">{key.intro}</p>
        <dl className="cp-key__list">
          {key.terms.map(({ term, meaning }) => (
            <div key={term}>
              <dt>{term}</dt>
              <dd>{meaning}</dd>
            </div>
          ))}
        </dl>
      </div>
    </details>
  );
}
