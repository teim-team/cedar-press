import { useEffect, useMemo, useState } from "react";
import { apiAvailable, fetchReleases } from "../../api.js";
import { canReadCedarPress } from "./pressAccess.js";
import { startArticleRequest, visibleArticleState } from "./articleRequest.js";
import { connectedReleaseModel, previewReleaseModel } from "./pressReleases.js";

const PREVIEW = previewReleaseModel();
export function useReleaseFeed(user, authLoading = false) {
  const connected = apiAvailable();
  const enabled = connected && !authLoading && Boolean(user) && canReadCedarPress(user);
  const owner = useMemo(() => ({ user, connected, authLoading }), [user, connected, authLoading]);
  const [state, setState] = useState(null);
  useEffect(() => {
    if (!enabled) return undefined;
    return startArticleRequest(
      async (options) => connectedReleaseModel(await fetchReleases(options)),
      (next) => setState({ ...next, owner }),
    );
  }, [enabled, owner]);
  if (!connected) return { status: "preview", data: PREVIEW };
  return visibleArticleState(state, owner, enabled);
}
