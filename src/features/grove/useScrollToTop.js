// REVIEW OWNER: Havala
//
// Client routing keeps the old scroll position, so opening an article from a
// card halfway down the reader landed the new page halfway down too. Every
// Press page that can be reached mid-scroll starts at its own top instead.
//
// The one exception is an arrival WITH a fragment ("Make your own" lands on
// /press#grove): the fragment owns the scroll and this hook must not fight
// it, so it stands down when a hash is present.

import { useEffect } from "react";
import { useLocation } from "react-router";

export function useScrollToTop(key) {
  const { hash } = useLocation();
  useEffect(() => {
    if (hash) return;
    window.scrollTo(0, 0);
  }, [key, hash]);
}
