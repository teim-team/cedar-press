// The published ten-row samples, fetched once each and kept.
//
// Lifted out of PressExplore unchanged when the record page and the entity
// page came along: three surfaces reading the same files with three copies of
// the fetch is three chances for one of them to cache differently or to keep
// a result the others dropped.
//
// WHAT IS LOADED IS STATE, NOT A REF
// Each sample is kept whether or not it is still selected; a fetch that
// finishes after the selection moved on is still a fetch that finished.
// `pending` holds the promise for a fetch in flight so a second effect run
// (React's strict-mode rehearsal, or a fast change of selection) never starts
// it twice. Each resource ends loading, loaded or failed, and the caller says
// which of its tables it could not read.
import { useEffect, useMemo, useRef, useState } from "react";

import { EMPTY_REGISTER, parseCsv, universalRows } from "./explore.js";

/**
 * `tables` is a list of `{ key, path }`. Returns the rows of every table that
 * has answered, in universal form; the keys of those that could not be read;
 * the raw column order per table; and whether anything is still in flight.
 */
export function useSampleRows(tables, register = EMPTY_REGISTER) {
  const [loaded, setLoaded] = useState(() => new Map());
  const pending = useRef(new Map());
  const wanted = tables.map((t) => t.path).join("|");
  useEffect(() => {
    for (const t of tables) {
      if (loaded.has(t.path) || pending.current.has(t.path)) continue;
      const promise = fetch(t.path)
        .then(async (r) => (r.ok ? parseCsv(await r.text()) : null))
        .catch(() => null)
        .then((parsed) => {
          pending.current.delete(t.path);
          setLoaded((prev) => (prev.has(t.path) ? prev : new Map(prev).set(t.path, parsed)));
        });
      pending.current.set(t.path, promise);
    }
    // `wanted` is the list of paths; `tables` is rebuilt each render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wanted, loaded]);
  return useMemo(() => {
    const rows = [];
    const missing = [];
    const columns = new Map();
    let loading = false;
    for (const t of tables) {
      if (!loaded.has(t.path)) { loading = true; continue; }
      const parsed = loaded.get(t.path);
      if (!parsed) { missing.push(t.key); continue; }
      columns.set(t.key, parsed.columns);
      rows.push(...universalRows(t.key, parsed.rows, register));
    }
    return { rows, missing, columns, loading };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wanted, loaded, register]);
}
