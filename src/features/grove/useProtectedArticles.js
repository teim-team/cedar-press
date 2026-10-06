import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchArticle, fetchArticles } from "../../api.js";
import { canReadCedarPress } from "./pressAccess.js";
import { startArticleRequest, visibleArticleState } from "./articleRequest.js";

function useArticleResource(user, slug) {
  const enabled = Boolean(user) && canReadCedarPress(user);
  // A Retry is a new attempt, and a new owner: the failed state is hidden
  // (reads as loading) the moment it is pressed, exactly as a new reader's
  // would be, and the request runs again.
  const [attempt, setAttempt] = useState(0);
  // Object identity also isolates sign-out/sign-in with the same email.
  const owner = useMemo(() => ({ user, slug, attempt }), [user, slug, attempt]);
  const [state, setState] = useState(null);
  useEffect(() => {
    if (!enabled) return undefined;
    return startArticleRequest(
      (options) => slug === null ? fetchArticles(options) : fetchArticle(slug, options),
      (next) => setState({ ...next, owner }),
    );
  }, [enabled, owner, slug]);
  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { ...visibleArticleState(state, owner, enabled), retry };
}

export function useProtectedArticles(user) {
  return useArticleResource(user, null);
}

export function useProtectedArticle(user, slug) {
  return useArticleResource(user, slug);
}
