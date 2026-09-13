// Whether the viewport is a phone's. Shared by the viewer, where the table
// becomes a list of records, and the gate's collection stage, which moves
// under the row that opened it. One breakpoint, stated once, so the two
// surfaces cannot disagree about where a phone begins.
import { useEffect, useState } from "react";

const QUERY = "(max-width: 720px)";

export function useNarrow(query = QUERY) {
  const [narrow, setNarrow] = useState(() => typeof window !== "undefined" && !!window.matchMedia?.(query).matches);
  useEffect(() => {
    const media = window.matchMedia?.(query);
    if (!media) return undefined;
    const onChange = () => setNarrow(media.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [query]);
  return narrow;
}
