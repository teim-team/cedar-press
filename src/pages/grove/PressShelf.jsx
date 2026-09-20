// REVIEW OWNER: Havala
//
// The shelves.
//
// One full-bleed band per tier, alternating filled and plain, so the tiers
// are what divide the page.
//
// A band is two halves. On the left the tier says what it is and lays out its
// collections as square badges. On the right, the space beside them is the
// reader: hover or focus a badge and it tells you what that collection is,
// how far back it goes and whether you can take it right now. That space used
// to be empty, and a square cannot say what a collection is without turning
// back into the card this replaced.
//
// A badge opens its collection in the viewer below and lights up; the
// reader beside the grid describes the collection and carries its sample
// download, on every pointer. That replaced "a badge is the download"
// (2026-09-05 review): a reader who clicks a collection wants to see its
// records, and the file is one more click in the panel that says what it
// is. A locked badge clicks too: it walks you to the panel that says what
// opens it. What's New is the one page that tracks changes.
//
// THE TWO SHELVES INVERT
// Cedar Press sits on teal with white tiles and teal marks; Cedar Press+ sits
// on white with teal tiles and white marks. Same two colours both times,
// swapped, which is what makes them read as one set rather than as an
// available thing and a greyed-out thing. A locked tile looks like its
// shelf; the band's own eyebrow and the reader panel carry the lock.
//
// Tiles lay out six across on a wide screen, one row a shelf, so the two
// tiers read as two rows of six; below that width the grid wraps by itself.
//
// THE ACTIVE COLLECTION IS SHARED, AND SELECTION IS NOT HOVER
// The shelf holds two things: the collection the pointer is on (the reader
// follows it) and the collection the viewer below is showing (its tile
// stays lit). Clicking a tile selects it in the viewer; choosing one in the
// viewer lights its tile; hovering changes what is described, never what
// is selected.
//
// FILTERED TO DATA, THIS IS THE READER'S OWN SHELF
// No locked band and no Cedar Grove. Somebody who asked to see the
// collections asked for the ones they can open, and answering with an upsell
// answers a different question. Everything else still shows both.
//
// The lock is a client-side affordance. `pressAccess` says so in its own
// header; the server has to answer identically before real data sits behind
// any of this.

import { Suspense, lazy, useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link } from "react-router";

import { PageBoundary } from "./PageBoundary.jsx";
import { appUrl } from "../../features/grove/appLink.js";
import { EVENT } from "../../features/grove/telemetry.js";
import { PRESS_TIERS } from "../../features/grove/pressCatalog";
import { TBN_PLANS_URL } from "../../features/grove/pressArticles";
// The viewer is the largest thing on the site (its own module, the contracts
// and the codebook), and it IS this page now, so it is fetched as the page
// is rather than after a shelf the reader had to scroll past first.
const PressExplore = lazy(() => import("./PressExplore"));
import { TierName } from "./TierName";

/**
 * Cedar Grove is not a fourth shelf holding one collection. It carries
 * everything Cedar Press does, its own exclusives, and the harmonized public
 * data, so its band shows all of that rather than the single badge that made
 * the tier look smaller than the two above it.
 */


/**
 * Marks the band once it has been scrolled to, so the badges can arrive
 * rather than being there already. One-way: a band that has been seen stays
 * seen, because re-animating on the way back up is the thing that makes a
 * page feel restless.
 */
function useReveal() {
  const ref = useRef(null);
  // Anywhere without IntersectionObserver starts revealed, decided at mount
  // rather than corrected by an effect: a band that flashes in on a browser
  // that cannot observe it is worse than one that was simply always there.
  const [seen, setSeen] = useState(() => typeof IntersectionObserver === "undefined");
  // A band that is already on the first screen was never scrolled to, so it
  // is not a reveal — same reasoning as useFadeIn. It is marked seen before
  // the browser paints and its badges do not run their staggered rise, so
  // the shelf is part of the page arriving rather than a second arrival
  // 45ms-per-badge behind it.
  const [instant, setInstant] = useState(false);
  useLayoutEffect(() => {
    const node = ref.current;
    if (!node || seen) return;
    // Flushed before paint, so the band never renders at opacity 0 first.
    if (node.getBoundingClientRect().top < (window.innerHeight || 0) * 1.1) {
      setInstant(true);
      setSeen(true);
    }
  }, [seen]);
  useEffect(() => {
    const node = ref.current;
    if (!node || seen) return undefined;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setSeen(true);
          observer.disconnect();
        }
      },
      { rootMargin: "-8% 0px -8% 0px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [seen]);
  return [ref, seen, instant];
}


/**
 * Cedar Grove, as a bridge rather than a second storefront.
 *
 * This was a page-width band with a page-sized headline, its own six-item
 * capability grid and a four-column list of the public data Grove harmonizes.
 * Sitting under a reader's own collections it read as a second product's home
 * page bolted to the foot of the first, and the owner's note was blunt: it had
 * not been updated. It is one band now. Three lines of argument, the price,
 * and a link. Everything cut from it is on Grove's own page, which is where a
 * reader who wants it is going anyway.
 *
 * It carried Gaming Intelligence as a Grove exclusive until 2026-09-04, when
 * that promise was withdrawn: the collection is still being built, and a
 * storefront that previews it is selling a cadence nobody has measured.
 */
function GroveTeaser({ tier }) {
  const [ref, seen, instant] = useReveal();
  return (
    // id="grove": the address of the Cedar Grove case. Article figures say
    // "Built in Cedar Grove. Make your own" and land here.
    <section ref={ref} id="grove" className={`cp-gt${seen ? " is-in" : ""}${instant ? " cp-reveal--now" : ""}`} aria-label="Cedar Grove">
      <div className="cp-gt__bar">
        <div className="cp-gt__say">
          <span className="cp-sec__band">Cedar Grove</span>
          <h3 className="cp-gt__title">The same collections, in a workspace built to interrogate them.</h3>
          <p className="cp-gt__body">
            Visualize and analyze across every collection at once, share the result with everyone
            you work with, and get each new Lumecon dataset as it lands, beside harmonized Census,
            BLS and BEA data on the same entities and geographies.
          </p>
        </div>
        <div className="cp-gt__buy">
          <p className="cp-gt__pricehead">${tier.price.toLocaleString("en-US")} a year</p>
          <p className="cp-gt__fine">Unlimited users in one organization</p>
          <a className="cp-band__cta" href={appUrl("/app/grove")} target="_blank" rel="noreferrer">
            See Cedar Grove <span aria-hidden="true">&#8594;</span>
          </a>
        </div>
      </div>
    </section>
  );
}

/**
 * THE COLLECTIONS PAGE IS THE TABLE.
 *
 * Owner, 2026-09-20: "In the app, the table should be the Collections page,
 * not something placed after a shelf page. The shelf still has a role, but
 * only as the catalog/selection mechanism integrated into the rail. Do not
 * make people browse tiles, scroll, then arrive at a second table
 * experience."
 *
 * So the tier bands are gone from this page. They were a catalogue, and the
 * explorer's rail is now the catalogue — keeping both asked a reader to
 * choose a collection twice, in two different grammars, before reaching a
 * record.
 *
 * WHAT THE BANDS DID THAT THE RAIL MUST KEEP DOING. Two things, and both
 * moved rather than vanished: a collection's description, which is the
 * pane's own header and its "About this collection" disclosure, and the
 * per-shelf "download all samples", which is now an action inside the rail's
 * shelf heading. `Band` and its reader panel are deleted with this change
 * rather than left unrendered.
 *
 * The Cedar Grove case stays at the foot, and keeps `id="grove"`: articles
 * link to /data#grove and that address has to keep resolving.
 */
export default function PressShelf({ user }) {
  const grove = PRESS_TIERS.find((tier) => !tier.storefront);
  return (
    <div id="catalog" className="cp-bands cp-bands--table">
      <PageBoundary what="The viewer">
        <Suspense fallback={<section className="cp-sec" aria-busy="true" aria-label="Explore the collections" />}>
          <PressExplore user={user} />
        </Suspense>
      </PageBoundary>
      {grove ? <GroveTeaser tier={grove} /> : null}
    </div>
  );
}
