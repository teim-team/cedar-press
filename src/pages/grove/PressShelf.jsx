import { Suspense, lazy } from "react";

import { appUrl } from "../../features/grove/appLink.js";
import { PageBoundary } from "./PageBoundary.jsx";

const PressExplore = lazy(() => import("./PressExplore"));

export default function PressShelf({ user }) {
  return (
    <div id="catalog" className="cp-bands cp-bands--table">
      <PageBoundary what="The viewer">
        <Suspense fallback={<section className="cp-sec" aria-busy="true" aria-label="Explore the collections" />}>
          <PressExplore user={user} />
        </Suspense>
      </PageBoundary>

      <p id="grove" className="cp-grove-exit">
        <strong>Cedar Grove</strong> brings these collections into a shared workspace for analysis.
        <a href={appUrl("/app/grove")} target="_blank" rel="noreferrer">
          Open Cedar Grove <span aria-hidden="true">&#8594;</span>
        </a>
      </p>
    </div>
  );
}
