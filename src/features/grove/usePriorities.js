// The priorities and this subscription's influence, from the service when
// it is connected and from the seed when it is not, with the difference
// stated rather than hidden: a build without the service shows the list
// with no counts and says that counting begins with the service.

import { useCallback, useEffect, useState } from "react";

import { apiAvailable, fetchInfluence, fetchPriorities, movePoints } from "../../api.js";
import { SEED_PRIORITIES } from "./pressPriorities.js";

export function usePriorities({ signedIn }) {
  const connected = apiAvailable();
  const [priorities, setPriorities] = useState(SEED_PRIORITIES);
  const [influence, setInfluence] = useState(null);
  // "static": no service in this build. "signed-out": a service, nobody
  // signed in. "loading" until the first answer, then "ok" or "failed".
  const [answered, setAnswered] = useState(null);
  const status = !connected ? "static" : !signedIn ? "signed-out" : (answered ?? "loading");
  const [error, setError] = useState(null);

  const reload = useCallback(async (signal) => {
    if (!connected || !signedIn) return;
    try {
      const [list, card] = await Promise.all([fetchPriorities({ signal }), fetchInfluence({ signal })]);
      if (signal?.aborted) return;
      setPriorities(list.priorities);
      setInfluence(card);
      setAnswered("ok");
      setError(null);
    } catch (e) {
      if (signal?.aborted) return;
      setAnswered("failed");
      setError(e?.message ?? "The service did not answer.");
    }
  }, [connected, signedIn]);

  useEffect(() => {
    const controller = new AbortController();
    // After the commit, not during it: every state the read sets is set
    // once the service has answered.
    Promise.resolve().then(() => reload(controller.signal));
    return () => controller.abort();
  }, [reload]);

  const move = useCallback(async (priorityId, points) => {
    const result = await movePoints({ priorityId, points });
    // The service answers with the priority's new totals and this
    // subscription's balance; the rest of the card is re-read.
    setPriorities((prev) => prev.map((p) => (p.id === priorityId ? { ...p, ...result.priority } : p)));
    await reload();
    return result;
  }, [reload]);

  return { priorities, influence, status, error, connected, reload, move };
}
