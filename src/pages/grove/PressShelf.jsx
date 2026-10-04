import { Suspense, lazy } from "react";

import { PageBoundary } from "./PageBoundary.jsx";
import { apiAvailable } from "../../api.js";
import { loadCodebook } from "../../features/grove/codebook.js";

// The viewer reads the codebook synchronously for its labels, so its chunk
// and the codebook arrive together (codebook.js); a failure of either is the
// boundary's "did not load".
const PressExplore = lazy(() => Promise.all([import("./PressExplore"), loadCodebook()]).then(([page]) => page));
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
