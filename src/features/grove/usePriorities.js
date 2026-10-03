// Private balances belong to the current authenticated account and plan.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiAvailable, fetchInfluence, fetchPriorities, movePoints, submitResearchRequest } from "../../api.js";
import { resolveTier } from "../../workspaceTier.js";
import { canReadCedarPress } from "./pressAccess.js";
import { createPrioritySession, visiblePriorityState } from "./pressPriorities.js";

export function usePriorities({ user }) {
  const connected = apiAvailable();
  const enabled = Boolean(user) && canReadCedarPress(user);
  const tier = resolveTier(user);
  // Re-login with the same email is a new owner; a plan change is too.
  const owner = useMemo(() => ({ user, tier }), [user, tier]);
  const [state, setState] = useState(null);
  const active = useRef(null);
  useEffect(() => {
    if (!connected || !enabled) return undefined;
    const session = createPrioritySession({ fetchPriorities, fetchInfluence, movePoints, submitResearchRequest,
      publish: (next) => setState({ ...next, owner }) });
    active.current = { owner, session };
    void session.reload();
    return () => {
      session.dispose();
      if (active.current?.session === session) active.current = null;
    };
  }, [connected, enabled, owner]);
  const currentSession = useCallback(() => {
    if (!connected || !enabled || active.current?.owner !== owner) {
      throw Object.assign(new Error("The account session changed."), { name: "AbortError" });
    }
    return active.current.session;
  }, [connected, enabled, owner]);
  const reload = useCallback(() => currentSession().reload(), [currentSession]);
  const move = useCallback((id, points) => currentSession().move(id, points), [currentSession]);
  const submit = useCallback((args) => currentSession().submit(args), [currentSession]);
  return { ...visiblePriorityState(state, owner, { connected, enabled }), connected, reload, move, submit };
}
