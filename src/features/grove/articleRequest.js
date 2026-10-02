/** A disposed request can never put subscriber content back into the UI. */
export function startArticleRequest(fetcher, publish) {
  const controller = new AbortController();
  let active = true;
  Promise.resolve()
    .then(() => fetcher({ signal: controller.signal }))
    .then(
      (data) => { if (active) publish({ status: "ready", data }); },
      (error) => {
        if (active) publish({
          status: error?.status === 404 ? "not-found" : "unavailable",
          data: null,
        });
      },
    );
  return () => {
    active = false;
    controller.abort();
  };
}

/** Hide an old owner's data during render, before effect cleanup runs. */
export function visibleArticleState(state, owner, enabled) {
  if (!enabled) return { status: "idle", data: null };
  return state?.owner === owner
    ? state
    : { status: "loading", data: null };
}
