/**
 * PURPOSE
 * The pages, and how each arrives.
 *
 * The reader (CedarPress) is the gate and the overview, the first screen for
 * everyone, so it ships in the first bundle. The other nine are behind a
 * click and are fetched when first opened: shipping them up front made a
 * visitor on a slow connection wait for the Methods reference and the
 * Explore viewer before the sign-in form could paint. Measured at 400 kbps
 * with everything in one bundle, 184 kB gzipped and nine seconds to first
 * paint; split, the first bundle is a third smaller and the viewer's 38 kB
 * arrives only on the Collections page.
 *
 * A chunk that fails to arrive (the connection dropped between clicks, or
 * a deployment replaced the hashed assets under an open tab) rejects the
 * lazy import; PageBoundary.jsx catches it and offers the reload that
 * fetches the current assets.
 */
import { lazy } from "react";

export { default as CedarPress } from "./CedarPress.jsx";

export const CedarPressArticles = lazy(() => import("./CedarPressArticles.jsx"));
export const CedarPressData = lazy(() => import("./CedarPressData.jsx"));
export const CedarPressArticle = lazy(() => import("./CedarPressArticle.jsx"));
export const CedarPressMethods = lazy(() => import("./CedarPressMethods.jsx"));
export const CedarPressResearchAccess = lazy(() => import("./CedarPressResearchAccess.jsx"));
export const CedarPressSettings = lazy(() => import("./CedarPressSettings.jsx"));
export const CedarPressPriorities = lazy(() => import("./CedarPressPriorities.jsx"));
export const CedarPressTribalRequest = lazy(() => import("./CedarPressTribalRequest.jsx"));
export const CedarPressWhatsNew = lazy(() => import("./CedarPressWhatsNew.jsx"));

/**
 * What a reader sees for the moment a page's code is on its way: the paper
 * ground and nothing on it, which is the page's own first frame, so a fast
 * connection never sees a spinner flash and a slow one sees the page it is
 * waiting for rather than a placeholder that will be torn down.
 */
export function PageArriving() {
  return <div className="teim-rd teim-rd--paper" aria-busy="true" style={{ minHeight: "100vh" }} />;
}
