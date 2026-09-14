// The chrome every reader page shares: the masthead and its section nav, the
// way back out of a leaf page, and one footer carrying the whole map.
//
// One component each, because the service runs across several pages now and
// three copies of a footer drift three ways — which is exactly what had
// happened: every page carried its own two-link version, so where the footer
// took you depended on where you already were.
import { useEffect, useRef } from "react";
import { Link, NavLink } from "react-router";

import { useAuth } from "../../context/useAuth";
import { contactHref } from "../../features/grove/appLink.js";
import { useNarrow } from "../../features/grove/useNarrow.js";

/**
 * The reader's initials, from the address. Two letters where the address
 * has a separator to take them from, one otherwise.
 */
/** The brand mark, served from public/. One constant so both lockups agree.
 *
 * The all-teal mark is the current one. There is an older cut with a gold arc
 * and dot still sitting in lumecon-website's brand folder; it is superseded,
 * and the two are otherwise the same drawing, so it is easy to reach for the
 * wrong file and hard to see that you have. */
const MARK = "/brand/lumecon-logo-mark-teal.png";

function initialsOf(email) {
  const local = String(email ?? "").split("@")[0];
  const parts = local.split(/[._-]+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return (local.slice(0, 2) || "?").toUpperCase();
}

import { LUMECON_URL, TBN_URL } from "../../features/grove/pressArticles";
import {
  PRESS_ARTICLES_PATH,
  PRESS_DATA_PATH,
  PRESS_METHODS_PATH,
  PRESS_PRIORITIES_PATH,
  PRESS_PATH,
  PRESS_REQUEST_PATH,
  PRESS_SETTINGS_PATH,
  PRESS_WHATS_NEW_PATH,
} from "../../features/grove/pressRoutes";

// The order the owner set, 2026-09-14: the collections are the product, the
// briefs are what Cedar wrote from them, and Priorities is where a subscriber
// changes what comes next. What's new and Methods are reference, so they
// follow. The same order runs in the hub tiles and the footer, because three
// navigations in three orders is three different maps of one site.
const NAV = [
  { id: "data", label: "Collections", to: PRESS_DATA_PATH },
  { id: "articles", label: "Research Briefs", to: PRESS_ARTICLES_PATH },
  { id: "priorities", label: "Priorities", to: PRESS_PRIORITIES_PATH },
  { id: "whats-new", label: "What’s new", to: PRESS_WHATS_NEW_PATH },
  { id: "methods", label: "Methods", to: PRESS_METHODS_PATH },
];

/**
 * The masthead: the wordmark, the section nav and who is signed in.
 *
 * The nav is on every page rather than a menu the front page hands out once,
 * so a reader can cross the service from wherever they landed — a citation
 * link, a shared brief — without going home first. `section` marks which
 * entry is current; a leaf page passes the section it belongs to (an article
 * marks Articles), so the nav still says where you are.
 *
 * `nav={false}` is for the public program pages read by someone signed out:
 * every section link would land them on the gate, and a row of doors that
 * all open onto a paywall reads as a broken site rather than a map. The
 * wordmark still leads home.
 */
/**
 * A disclosure that closes on Escape and on a click outside it.
 *
 * Both menus in the masthead are native `<details>`: they work with no state,
 * a keyboard reaches them, and a screen reader announces them. What details
 * does not do on its own is close when the reader looks elsewhere, which is
 * what a menu in a header has to do.
 */
function useDismissable() {
  const ref = useRef(null);
  useEffect(() => {
    const node = ref.current;
    if (!node) return undefined;
    const close = (refocus) => {
      if (!node.open) return;
      node.open = false;
      if (refocus) node.querySelector("summary")?.focus();
    };
    const onKey = (event) => { if (event.key === "Escape") close(true); };
    const onDown = (event) => { if (!node.contains(event.target)) close(false); };
    node.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown);
    return () => {
      node.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown);
    };
  }, []);
  return ref;
}

/**
 * Who is signed in, as one control on the masthead's own row.
 *
 * THE HEADER WAS FOUR ROWS ON A PHONE. Review, 2026-09-15: "the logo occupies
 * one row, the avatar and Sign out another, and navigation another two rows.
 * That creates a large header before the page itself begins. The standalone
 * Sign out placement looks like an accidental wrap." It was exactly that — a
 * flex row with `flex: 1 1 100%` on the user block under 640px, which is a
 * wrap dressed up as a layout.
 *
 * So the avatar sits beside the wordmark at every width and everything it
 * used to spell out — the address, the settings page, signing out — is inside
 * it. A header is for saying where you are, not for carrying an errand.
 */
function AccountMenu({ user, onSignOut }) {
  const ref = useDismissable();
  return (
    <details className="cp-acct" ref={ref}>
      <summary className="cp-acct__btn" aria-label={`Account for ${user.email}`}>
        <span className="cp-avatar" aria-hidden="true">{initialsOf(user.email)}</span>
        <span className="cp-acct__cue" aria-hidden="true">&#9662;</span>
      </summary>
      <div className="cp-acct__menu">
        <span className="cp-acct__who">{user.email}</span>
        <Link className="cp-acct__item" to={PRESS_SETTINGS_PATH}>Account and settings</Link>
        <button type="button" className="cp-acct__item cp-acct__out" onClick={onSignOut}>
          Sign out
        </button>
      </div>
    </details>
  );
}

/**
 * The sections, as one control on a phone.
 *
 * Five links spaced across two rows is a nav that costs a quarter of the
 * screen to say what a reader already knows. The summary names the section
 * they are in; the panel is the same five links, in the same order as the
 * wide nav, because two navigations in two orders is two maps.
 */
function SectionMenu({ section }) {
  const ref = useDismissable();
  const here = section === "home" ? "Overview" : NAV.find((item) => item.id === section)?.label ?? "Overview";
  return (
    <details className="cp-navm" ref={ref}>
      <summary className="cp-navm__btn">
        <span className="cp-navm__here">{here}</span>
        <span className="cp-navm__cue" aria-hidden="true">&#9662;</span>
      </summary>
      <nav className="cp-navm__menu" aria-label="Sections">
        <NavLink className="cp-navm__item" to={PRESS_PATH} end>Overview</NavLink>
        {NAV.map((item) => (
          <NavLink
            key={item.id}
            className="cp-navm__item"
            to={item.to}
            aria-current={item.id === section ? "page" : undefined}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </details>
  );
}

export function PressMast({ user, onSignOut, section = null, nav = true }) {
  const home = section === "home";
  // The distribution line is for visitors deciding what this is; a
  // subscriber already inside the product does not need the masthead
  // re-introducing it on every page. Read from the session directly, since
  // not every page threads `user` into the masthead.
  const { user: signedIn } = useAuth();
  // One nav or the other, never both: two copies of five links in the DOM
  // make every "Collections" link ambiguous to anything that looks for one.
  const narrow = useNarrow("(max-width: 760px)");
  return (
    <>
    {/* The first stop for a keyboard or a screen reader: the nav and the
        masthead are the same on every page, and skipping them is the
        difference between reading a page and traversing it. */}
    <a className="cp-skip" href="#cp-main">Skip to content</a>
    <header className="cp-mast">
      <div className="cp-mast__top">
        {/* The mark and the wordmark as one lockup. Cedar Press is built by
            Lumecon and carries Lumecon's mark, the same way the platform
            does — there is no separate Cedar Press mark, and inventing one
            would put a second identity on a product that has one.

            aria-hidden with the wordmark beside it: the words are the
            accessible name, and a screen reader announcing an image and then
            the same words is a stutter. */}
        {home ? (
          <span className="cp-mast__lockup">
            <img className="cp-mast__mark" src={MARK} alt="" aria-hidden="true" />
            <span className="cp-mast__word">CEDAR PRESS</span>
          </span>
        ) : (
          <Link className="cp-mast__lockup" to={PRESS_PATH}>
            <img className="cp-mast__mark" src={MARK} alt="" aria-hidden="true" />
            <span className="cp-mast__word">CEDAR PRESS</span>
          </Link>
        )}
        {/* Who made it and who sells it, said plainly — to visitors. "A ×
            partnership" left both questions open; a signed-in reader has
            already answered them. */}
        {signedIn ? null : (
          <span className="cp-mast__of">
            Built by <a href={LUMECON_URL} target="_blank" rel="noreferrer">Lumecon</a>. Available
            exclusively through{" "}
            <a href={TBN_URL} target="_blank" rel="noreferrer">Tribal Business News</a>.
          </span>
        )}
        {/* The section menu rides the same row as the lockup on a phone, so
            the whole header is one row rather than four. */}
        {nav && narrow ? <SectionMenu section={section} /> : null}
        {user ? <AccountMenu user={user} onSignOut={onSignOut} /> : null}
      </div>
      {nav && !narrow ? (
        <nav className="cp-nav" aria-label="Sections">
          <NavLink className="cp-nav__item" to={PRESS_PATH} end>
            Overview
          </NavLink>
          {NAV.map((item) => (
            <NavLink
              key={item.id}
              className="cp-nav__item"
              to={item.to}
              aria-current={item.id === section ? "page" : undefined}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      ) : null}
    </header>
    </>
  );
}

/**
 * The way out of a leaf page, back to the section that holds it. The nav
 * above covers the sections themselves; this is for a piece inside one,
 * where "the list I came from" is a different answer than "the section".
 */
export function PressBack({ label = "All of Cedar Press", to = PRESS_PATH }) {
  return (
    <Link className="cp-ar__back cp-back" to={to}>
      <span aria-hidden="true">&#8592;</span> {label}
    </Link>
  );
}

/**
 * The footer: the whole map, then who publishes it, then the promise.
 *
 * One footer, navy, on every page — pages that ended in white dissolved
 * rather than finished. The thin teal edge is the footer's own seam and
 * renders everywhere, even against a teal band above it: the component owns
 * the line, so the same footer means the same ending on every page. `flush`
 * is for a page whose last section is already navy (the reader's close): it
 * removes the gap, never the seam.
 *
 * The tribal-governments line makes the governance pathway discoverable
 * from every page without turning it into a marketing element: a council
 * office should not need a subscription to find out how to ask.
 *
 * `nav={false}` mirrors the masthead's slim mode for signed-out readers of
 * the public program pages: the section links all end at the gate for them,
 * so the footer keeps only the way home and the standing lines.
 */
export function PressFoot({ flush = false, nav = true }) {
  return (
    <footer className={`cp-foot cp-foot--deep${flush ? " cp-foot--flush" : ""}`}>
      <div className="cp-foot__in">
        <nav className="cp-foot__nav" aria-label="Cedar Press">
          <Link to={PRESS_PATH}>Cedar Press</Link>
          {nav ? (
            <>
              <Link to={PRESS_DATA_PATH}>Collections</Link>
              <Link to={PRESS_ARTICLES_PATH}>Research Briefs</Link>
              <Link to={PRESS_PRIORITIES_PATH}>Priorities</Link>
              <Link to={PRESS_WHATS_NEW_PATH}>What&rsquo;s new</Link>
              <Link to={PRESS_METHODS_PATH}>Methods</Link>
              <Link to={PRESS_SETTINGS_PATH}>Settings</Link>
              {/* Contact came off the hub's six doors when Priorities took
                  its place. It is a mail link rather than a section, and this
                  is where a reader looks for one. */}
              <a href={contactHref("Cedar Press")}>Contact</a>
            </>
          ) : null}
        </nav>
        <div className="cp-foot__meta">
          <span className="cp-foot__gov">
            <Link to={PRESS_REQUEST_PATH}>
              For tribal governments: request your records <span aria-hidden="true">&#8594;</span>
            </Link>
          </span>
          <span>
            <a href={TBN_URL} target="_blank" rel="noreferrer">tribalbusinessnews.com</a>
            {" · "}
            <a href={LUMECON_URL} target="_blank" rel="noreferrer">lumecon.ai</a>
          </span>
        </div>
      </div>
    </footer>
  );
}
