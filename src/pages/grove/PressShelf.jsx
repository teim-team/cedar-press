import { Suspense, lazy } from "react";

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
    </div>
  );
}
