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
import { EVENT, track } from "../../features/grove/telemetry.js";
import { canOpenDataset, coverageFrom, coverageLabel } from "../../features/grove/pressAccess";
import { downloadAll, downloadCsv, hasReleaseFile } from "../../features/grove/pressDownload";
import {
  PRESS_CATALOG_BY_ID,
  PRESS_TIERS,
  collectionsOnShelf,
} from "../../features/grove/pressCatalog";
import { freshnessLine } from "../../features/grove/pressReleases";
import { TBN_PLANS_URL } from "../../features/grove/pressArticles";
import { LAUNCH_COLLECTION } from "../../features/grove/collection";
import { COLLECTION_ICONS } from "./pressCollectionIcons";
// The viewer is the largest thing on the site (its own module, the contracts
// and the codebook), and it is below the shelves: fetched when the page is,
// not before the gate can paint.
const PressExplore = lazy(() => import("./PressExplore"));
import { TierName } from "./TierName";
import { PRESS_METHODS_PATH } from "../../features/grove/pressRoutes";

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

function Badge({ entry, open, onEnter, active, selected, index, onLocked, onOpen }) {
  const className = `cp-badge${active || selected ? " is-on" : ""}${selected ? " is-selected" : ""}${open ? " cp-badge--act" : " cp-badge--locked"}`;
  // The selection is sticky on every pointer, not only touch: the read panel
  // carries its own actions (Ask Cedar, the touch download), and clearing on
  // mouse-leave or blur unmounted those buttons under the very pointer
  // traveling to click them. The panel changes when another tile is pointed
  // at, never back to the idle hint.
  const watch = { onMouseEnter: onEnter, onFocus: onEnter };
  const inner = (
    <>
      <span className="cp-badge__mark" aria-hidden="true">{COLLECTION_ICONS[entry.id]}</span>
      <span className="cp-badge__name"><TierName name={entry.short || entry.name} /></span>
    </>
  );
  // The badges arrive in sequence rather than all at once, which is what
  // makes a grid read as a shelf filling up instead of a page repainting.
  const style = { "--i": index };

  // Every tile answers a click on both shelves, and the cue says what the
  // answer is: an owned tile hands over the file (the down arrow is the
  // download), a locked one walks you to what opens it. Only the symbol
  // differs, so the two shelves keep one hover language.
  if (!open) {
    return (
      <li style={style}>
        <button type="button" className={className} onClick={onLocked} {...watch}>
          {inner}
          <span className="cp-badge__cue" aria-hidden="true">&#8594;</span>
          <span className="cp-badge__sr">See what opens {entry.name}</span>
        </button>
      </li>
    );
  }
  return (
    <li style={style}>
      <button type="button" className={className} onClick={() => onOpen(entry)} aria-pressed={selected} {...watch}>
        {inner}
        <span className="cp-badge__cue" aria-hidden="true">&#8595;</span>
        <span className="cp-badge__sr">Open {entry.name} in the viewer below</span>
      </button>
    </li>
  );
}

/** Whether Cedar has a profile to answer from for this collection. Every
 *  catalog collection has one now: the launch four answer from their releases
 *  and the rest from their catalog entries (collection_profiles.py), so only
 *  an entry outside the catalog — the harmonized public data — goes without
 *  the button. */
function hasCedarProfile(id) {
  return Boolean(PRESS_CATALOG_BY_ID[id]) || LAUNCH_COLLECTION.some((d) => d.id === id);
}

/** What the reader says about the collection under the cursor. */
function Detail({ entry, owned }) {
  // What the service said when it refused the file, connected; nothing
  // otherwise. A button that silently does nothing is the failure this
  // replaces. Keyed by the collection where it is rendered, so a refusal
  // never outlives the collection it was about.
  const [refusal, setRefusal] = useState(null);
  return (
    <div className="cp-read__on">
      <span className="cp-read__cap">
        {entry.kind === "public" ? "Harmonized public data" : "Cedar collection"}
      </span>
      <h4 className="cp-read__name"><TierName name={entry.name} /></h4>
      <p className="cp-read__blurb">{entry.blurb}</p>
      {entry.linkage ? (
        <p className="cp-read__link">
          <span className="cp-read__linkcap">The link</span>
          {entry.linkage}
        </p>
      ) : null}
      <p className="cp-read__foot">
        {coverageLabel(entry)}
        {" · "}
        {freshnessLine(entry.id) || (owned ? "Opens in the viewer below" : "Locked")}
      </p>
      {/* The download lives here, on every pointer: the panel says what the
          file is before the finger or the cursor takes it. "Sample", not
          the collection's name alone: what downloads is ten real rows of the
          collection's flagship table, not the collection. */}
      {owned ? (
        <button
          type="button"
          className="cp-read__act"
          onClick={() => {
            track(EVENT.collectionDownloaded, { collection: entry.id, shelf: entry.shelf });
            setRefusal(null);
            downloadCsv(entry).catch((error) => setRefusal(error?.message || "The download did not go through."));
          }}
        >
          <span aria-hidden="true">&#8595;</span>{" "}
          {hasReleaseFile(entry)
            ? `Download a ten-row sample of ${entry.short || entry.name}`
            : "Download the collection description (sample pending)"}
        </button>
      ) : null}
      {refusal ? <p className="cp-read__foot" role="alert">{refusal}</p> : null}
      {/* Cedar, already scoped: the reader looking at this description is
          one click from asking how the collection was built or what its
          headline figures are, without restating which collection. The
          event reaches the floating control without a prop path. */}
      {hasCedarProfile(entry.id) ? (
        <button
          type="button"
          className="cp-read__cedar"
          onClick={() =>
            window.dispatchEvent(
              new CustomEvent("cedar:ask-collection", {
                detail: { id: entry.id, name: entry.name },
              }),
            )
          }
        >
          Ask Cedar about this collection <span aria-hidden="true">&#8594;</span>
        </button>
      ) : null}
      {/* Where the entity-methodology link went when it came off the top of
          the page: a reader asking how this collection reaches its entities
          is already reading about this collection. */}
      <Link className="cp-read__method" to={`${PRESS_METHODS_PATH}#m-collections`}>
        How this collection is built <span aria-hidden="true">&#8594;</span>
      </Link>
    </div>
  );
}


function Band({ tier, user, index, hovered, setHovered, selectedId, onPick }) {
  const entries = collectionsOnShelf(tier.shelf);

  // Off the tier's own shelf, never off its first entry: Grove's band leads
  // with the collections Cedar Press also carries, so asking about entry
  // zero told a Cedar Press reader that Cedar Grove was their shelf.
  const owned = canOpenDataset(user, { shelf: tier.shelf });
  // The same years whether or not the reader owns the shelf: a locked band
  // shows what is inside it, and what is inside it does not shrink when it
  // opens. Rosters contribute nothing here — `coverageFrom` returns null for
  // them, and a shelf's earliest year must not be a harvest date.
  const starts = entries.map((entry) => coverageFrom(entry)).filter(Boolean);
  const from = starts.length ? Math.min(...starts) : null;
  // The reader follows the pointer; with nothing under it, it describes
  // the collection the viewer is showing.
  // THE PANEL IS 26REM OF RESERVED COLUMN; AT REST IT HELD NOTHING.
  // `.cp-band__in` lays each shelf out as tiles beside a 26rem panel, and the
  // panel only had a collection in it once a pointer was on a tile — so the
  // resting state of both shelves, which is the state anyone arriving sees,
  // was six tiles across 40% of the page and 60% of empty beside them.
  //
  // The instruction box that used to stand there was removed for good reason
  // (a caption on an empty frame). The answer is not to put the caption back
  // or to collapse the column — collapsing makes the whole grid jump the
  // first time a cursor crosses a tile. The panel was built to describe a
  // collection, so it opens describing one: the first on the shelf. Nothing
  // reserved, nothing empty, nothing that moves, and the shelf's first
  // download is one click away instead of one hover plus one click.
  const active =
    entries.find((entry) => entry.id === (hovered ?? selectedId)) || entries[0] || null;
  const [ref, seen, instant] = useReveal();

  // A locked tile's click walks the reader to the answer: the panel that
  // says what the collection is and carries the way in. The ring is so the
  // eye lands there even when the panel was already on screen.
  const readRef = useRef(null);
  const [pulse, setPulse] = useState(false);
  const pointAtUpgrade = () => {
    track(EVENT.lockedCollectionTapped, { shelf: tier.shelf });
    readRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    setPulse(true);
    window.setTimeout(() => setPulse(false), 900);
  };

  // A tile selects its collection in the viewer below and lights; the
  // reader keeps describing it, with the download, until the pointer moves
  // to another tile.
  const openTile = (entry) => {
    track(EVENT.collectionViewed, { collection: entry.id, shelf: tier.shelf });
    setHovered(entry.id);
    onPick(entry.id);
  };

  return (
    <section
      ref={ref}
      className={`cp-band cp-band--${index % 2 === 0 ? "fill" : "plain"}${seen ? " is-in" : ""}${instant ? " cp-reveal--now" : ""}`}
      aria-label={tier.name}
    >
      <div className="cp-band__in">
        {/* What this band is, top right, in the same line as the eyebrow. A
            reader scanning for the download should not have to infer it from
            a grid of squares. */}
        {/* THE PLAN, ITS COVERAGE, AND THE TILES.
            Review, 2026-09-15: "'Your shelf', 'Cedar Press', 'See what's
            happening', a descriptive sentence, coverage metadata, a hover
            instruction, and a separate instruction box are too many layers
            around six choices. A plan name, concise coverage information, and
            the collection tiles would be enough."
            So the eyebrow, the question, the promise and the footnote are
            gone. What a collection holds is in the panel the tile opens, and
            each tile's own dates are in it, which is what the footnote was
            pointing at. */}
        <div className="cp-band__head">
        <div className="cp-band__id">
          <h3 className="cp-band__name"><TierName name={tier.name} /></h3>
          {/* No price here: Tribal Business News owns Press payment, renewal
              and upgrades, and a number embedded in this catalog goes stale
              the moment the seller changes theirs. The CTA below walks the
              reader to the canonical price. */}
          {owned || tier.id === "grove" ? null : (
            <p className="cp-band__price">Sold through Tribal Business News</p>
          )}
          {owned || tier.id !== "grove" ? null : (
            <p className="cp-band__price">${tier.price.toLocaleString("en-US")} a year</p>
          )}
          {/* "As far back as", not "back to": the year is the deepest single
              collection and the rest reach back different distances, so the
              line says the shelf's floor and each tile's panel gives its own
              dates. */}
          <p className="cp-band__facts">
            {entries.length} collections
            {from ? ` · records as far back as ${from}` : ""}
            {owned ? " · yours to download" : ""}
          </p>
        </div>
        {/* The chip said "Collections you download" beside a facts line that
            ends "yours to download". One of the two was decoration. */}
        </div>

        <ul
          className="cp-band__grid"
          style={{ "--cols": Math.min(entries.length, 6) }}
        >
          {entries.map((entry, position) => (
            <Badge
              key={entry.id}
              index={position}
              entry={entry}
              open={owned}
              active={active?.id === entry.id}
              selected={selectedId === entry.id}
              onEnter={() => setHovered(entry.id)}
              onLocked={pointAtUpgrade}
              onOpen={openTile}
            />
          ))}
        </ul>

        {owned ? (
          <p className="cp-band__all">
            <button type="button" className="cp-band__allbtn" onClick={() => { track(EVENT.shelfDownloadedAll, { shelf: tier.shelf, count: entries.length }); downloadAll(entries); }}>
              <span aria-hidden="true">&#8595;</span> Download all {entries.length} samples
            </button>
          </p>
        ) : null}

        {/* Live, so a screen reader hears what the cursor shows. Polite, so
            it never cuts in while someone is reading something else. */}
        {/* The panel is not drawn when it has nothing to say: an empty
            bordered rectangle beside the tiles was the instruction box's
            frame outliving the instruction. A locked shelf keeps it, because
            the way in lives in it. */}
        <aside
          ref={readRef}
          className={`cp-read${pulse ? " is-pulse" : ""}${!active && owned ? " is-empty" : ""}`}
          aria-live="polite"
        >
          {/* The panel describes the collection under the pointer, and
              nothing when there is none: the instruction box that used to
              stand here said what a tile does to a reader who had not
              touched one yet, which is a caption on an empty frame. */}
          {active ? <Detail key={active.id} entry={active} owned={owned} /> : null}
          {owned ? null : tier.id === "grove" ? (
            // Grove is Lumecon-sold, so its door is the app's plan page.
            <a className="cp-band__cta" href={appUrl("/app/settings?tab=plan")} target="_blank" rel="noreferrer">
              Get <TierName name={tier.name} /> <span aria-hidden="true">&#8594;</span>
            </a>
          ) : (
            // Press tiers are sold by Tribal Business News; /app cannot
            // perform this upgrade, so the click goes to the plans page
            // where the action actually lives.
            <a className="cp-band__cta" href={TBN_PLANS_URL} target="_blank" rel="noreferrer">
              Get <TierName name={tier.name} /> at Tribal Business News{" "}
              <span aria-hidden="true">&#8594;</span>
            </a>
          )}
        </aside>
      </div>
    </section>
  );
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
 * Filtered to Data, this is a reader's own shelf and nothing else: no locked
 * band, no Cedar Grove. Somebody who asked to see the collections asked for
 * the ones they can open, and answering with an upsell is answering a
 * different question.
 */
export default function PressShelf({ user }) {
  const shelves = PRESS_TIERS.filter((tier) => tier.storefront);
  const grove = PRESS_TIERS.find((tier) => !tier.storefront);
  const [hovered, setHovered] = useState(null);
  // What the viewer shows (its tile stays lit), and the latest tile click,
  // numbered so clicking the same tile twice scrolls to the viewer twice.
  const [selectedId, setSelectedId] = useState(null);
  const [pick, setPick] = useState(null);
  const onPick = (id) => setPick((prev) => ({ id, n: (prev?.n ?? 0) + 1 }));
  return (
    <div id="catalog" className="cp-bands">
      {shelves.map((tier, index) => (
        <Band key={tier.id} tier={tier} user={user} index={index} hovered={hovered} setHovered={setHovered} selectedId={selectedId} onPick={onPick} />
      ))}
      <PageBoundary what="The viewer">
        <Suspense fallback={<section className="cp-sec" aria-busy="true" aria-label="Explore the collections" />}>
          <PressExplore user={user} pick={pick} onActive={setHovered} onSelected={setSelectedId} />
        </Suspense>
      </PageBoundary>
      {grove ? <GroveTeaser tier={grove} /> : null}
    </div>
  );
}
