/**
 * PURPOSE
 * The page's own title and description, so a tab, a history entry, a shared
 * link and a search result say which page they are.
 *
 * Every route rendered the same "Cedar Press", which is the client-routing
 * default: the document head is set once by index.html and nothing changes
 * it on navigation. A reader with the service open beside their work has
 * several identical tabs, and a link they send names nothing.
 *
 * The service name stays in the title rather than living only in the tab
 * icon, because a title is read out of context — in a bookmark bar, in a
 * search result, in a message.
 *
 * WHAT A CRAWLER READS
 * The description, the canonical address and the Open Graph pair follow the
 * page too, and a page behind the sign-in says `noindex`: robots.txt already
 * keeps crawlers off those paths, and a page that answers with a gate should
 * not be ranked as an answer. The three public pages (the door, the tribal
 * data request policy, research access) carry a description of their own,
 * which is what a search result shows under the title.
 */
import { useEffect } from "react";

const SERVICE = "Cedar Press";
export const SITE_ORIGIN = "https://cedarpress.ai";

/** The description index.html ships for the door; the fallback for every page. */
export const SITE_DESCRIPTION =
  "Trusted intelligence for Indian Country: original economic collections, data-driven research and transparent method. Built by Lumecon, available exclusively through Tribal Business News.";

function setMeta(selector, attribute, content) {
  const tag = document.head.querySelector(selector);
  if (tag) tag.setAttribute(attribute, content);
}

/**
 * @param {string} [title] the page's own name; none for the door
 * @param {object} [head]
 * @param {string} [head.description] what a search result shows under the title
 * @param {boolean} [head.index] whether a crawler may index the page; false behind the gate
 */
export function useDocumentTitle(title, { description = SITE_DESCRIPTION, index = false } = {}) {
  useEffect(() => {
    const full = title ? `${title} · ${SERVICE}` : `${SERVICE} — Trusted intelligence for Indian Country`;
    document.title = full;
    const path = window.location.pathname.replace(/\/+$/, "") || "/";
    const url = `${SITE_ORIGIN}${path === "/" ? "/" : path}`;
    setMeta('meta[name="description"]', "content", description);
    setMeta('link[rel="canonical"]', "href", url);
    setMeta('meta[property="og:title"]', "content", title || "Trusted intelligence for Indian Country");
    setMeta('meta[property="og:description"]', "content", description);
    setMeta('meta[property="og:url"]', "content", url);
    setMeta('meta[name="twitter:title"]', "content", title || "Trusted intelligence for Indian Country");
    setMeta('meta[name="twitter:description"]', "content", description);
    let robots = document.head.querySelector('meta[name="robots"]');
    if (!robots) {
      robots = document.createElement("meta");
      robots.setAttribute("name", "robots");
      document.head.appendChild(robots);
    }
    robots.setAttribute("content", index ? "index, follow" : "noindex, nofollow");
  }, [title, description, index]);
}
