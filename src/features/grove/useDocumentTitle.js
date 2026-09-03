/**
 * PURPOSE
 * The page's own title, so a tab, a history entry and a shared link say
 * which page they are.
 *
 * Every route rendered the same "Cedar Press", which is the client-routing
 * default: the document title is set once by index.html and nothing changes
 * it on navigation. A reader with the service open beside their work has
 * several identical tabs, and a link they send names nothing.
 *
 * The service name stays in the title rather than living only in the tab
 * icon, because a title is read out of context — in a bookmark bar, in a
 * search result, in a message.
 */
import { useEffect } from "react";

const SERVICE = "Cedar Press";

export function useDocumentTitle(title) {
  useEffect(() => {
    document.title = title ? `${title} · ${SERVICE}` : SERVICE;
  }, [title]);
}
