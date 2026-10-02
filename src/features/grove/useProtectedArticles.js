import { useEffect, useMemo, useState } from "react";
import { fetchArticle, fetchArticles } from "../../api.js";
import { canReadCedarPress } from "./pressAccess.js";
import { startArticleRequest, visibleArticleState } from "./articleRequest.js";

function useArticleResource(user, slug) {
  const enabled = Boolean(user) && canReadCedarPress(user);
  // Object identity also isolates sign-out/sign-in with the same email.
  const owner = useMemo(() => ({ user, slug }), [user, slug]);
  const [state, setState] = useState(null);
  useEffect(() => {
    if (!enabled) return undefined;
    return startArticleRequest(
      (options) => slug === null ? fetchArticles(options) : fetchArticle(slug, options),
      (next) => setState({ ...next, owner }),
    );
  }, [enabled, owner, slug]);
  return visibleArticleState(state, owner, enabled);
}

export function useProtectedArticles(user) {
  return useArticleResource(user, null);
}

export function useProtectedArticle(user, slug) {
  return useArticleResource(user, slug);
}
