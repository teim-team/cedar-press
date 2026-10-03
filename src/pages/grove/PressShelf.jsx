import { Suspense, lazy } from "react";

import { PageBoundary } from "./PageBoundary.jsx";
import { apiAvailable } from "../../api.js";

const PressExplore = lazy(() => import("./PressExplore"));
const ReleasedCollections = lazy(() => import("./ReleasedCollections.jsx"));

export default function PressShelf({ user }) {
  return (
    <div id="catalog" className="cp-bands cp-bands--table">
      <PageBoundary what="The viewer">
        <Suspense fallback={<section className="cp-sec" aria-busy="true" aria-label="Explore the collections" />}>
          {apiAvailable() ? <ReleasedCollections key={user?.id || user?.email || "anonymous"} /> : <PressExplore user={user} />}
        </Suspense>
      </PageBoundary>
    </div>
  );
}
