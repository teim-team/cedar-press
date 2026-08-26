// The chrome every reader page shares: the masthead and its section nav, the
// way back out of a leaf page, and one footer carrying the whole map.
//
// One component each, because the service runs across several pages now and
// three copies of a footer drift three ways — which is exactly what had
// happened: every page carried its own two-link version, so where the footer
// took you depended on where you already were.
import { Link, NavLink } from "react-router";

/**
 * The reader's initials, from the address. Two letters where the address
 * has a separator to take them from, one otherwise.
 */
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
  PRESS_PATH,
  PRESS_SETTINGS_PATH,
  PRESS_WHATS_NEW_PATH,
} from "../../features/grove/pressRoutes";

const NAV = [
  { id: "articles", label: "Articles", to: PRESS_ARTICLES_PATH },
  { id: "data", label: "Data", to: PRESS_DATA_PATH },
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
 */
export function PressMast({ user, onSignOut, section = null }) {
  const home = section === "home";
  return (
    <>
    {/* The first stop for a keyboard or a screen reader: the nav and the
        masthead are the same on every page, and skipping them is the
        difference between reading a page and traversing it. */}
    <a className="cp-skip" href="#cp-main">Skip to content</a>
    <header className="cp-mast">
      <div className="cp-mast__top">
        {/* The wordmark alone until the real Cedar Press logo lands: the
            ripple in public/ is one element of the Lumecon logo, not the
            service's mark, and half a logo is worse than none. */}
        {home ? (
          <span className="cp-mast__word">CEDAR PRESS</span>
        ) : (
          <Link className="cp-mast__word" to={PRESS_PATH}>CEDAR PRESS</Link>
        )}
        {/* Who made it and who sells it, said plainly. "A × partnership"
            left both questions open. */}
        <span className="cp-mast__of">
          Built by <a href={LUMECON_URL} target="_blank" rel="noreferrer">Lumecon</a>. Available
          exclusively through{" "}
          <a href={TBN_URL} target="_blank" rel="noreferrer">Tribal Business News</a>.
        </span>
        {user ? (
          <span className="cp-mast__user">
            <Link className="cp-avatar" to={PRESS_SETTINGS_PATH} title={user.email}>
              <span aria-hidden="true">{initialsOf(user.email)}</span>
              <span className="cp-avatar__sr">Account and settings for {user.email}</span>
            </Link>
            <button type="button" className="cp-split__linkbtn" onClick={onSignOut}>
              Sign out
            </button>
          </span>
        ) : null}
      </div>
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
 * `deep` continues the close band's navy instead of cutting back to paper
 * for six lines of chrome.
 */
export function PressFoot({ deep = false }) {
  return (
    <footer className={`cp-foot${deep ? " cp-foot--deep" : ""}`}>
      <div className="cp-foot__in">
        <nav className="cp-foot__nav" aria-label="Cedar Press">
          <Link to={PRESS_PATH}>Cedar Press</Link>
          <Link to={PRESS_ARTICLES_PATH}>Articles</Link>
          <Link to={PRESS_DATA_PATH}>Data</Link>
          <Link to={PRESS_WHATS_NEW_PATH}>What&rsquo;s new</Link>
          <Link to={PRESS_METHODS_PATH}>Methods</Link>
          <Link to={PRESS_SETTINGS_PATH}>Settings</Link>
        </nav>
        <div className="cp-foot__meta">
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
