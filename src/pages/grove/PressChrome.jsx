// The chrome every reader page shares: the masthead that says where you are
// and who is signed in, the way back to the hub, and one footer carrying the
// whole map. One component each, because the hub split the reader across
// several pages and three copies of a footer drift three ways — which is
// exactly what had happened: every page carried its own two-link version.
import { Link } from "react-router";

import { LUMECON_URL, TBN_URL } from "../../features/grove/pressArticles";
import {
  PRESS_ARTICLES_PATH,
  PRESS_DATA_PATH,
  PRESS_METHODS_PATH,
  PRESS_PATH,
  PRESS_REQUEST_PATH,
  PRESS_RESEARCH_PATH,
  PRESS_WHATS_NEW_PATH,
} from "../../features/grove/pressRoutes";

/**
 * The masthead.
 *
 * On the hub the wordmark is text (you are here) and the line beside it says
 * who made this and who sells it. On an inner page the wordmark is the way
 * home and that line becomes the page's own name, so the header always
 * answers "where am I" before anything else on the page does.
 */
export function PressMast({ user, onSignOut, page = null }) {
  const home = !page;
  return (
    <header className="cp-mast">
      {home ? (
        <span className="cp-mast__word">CEDAR PRESS</span>
      ) : (
        <Link className="cp-mast__word" to={PRESS_PATH}>CEDAR PRESS</Link>
      )}
      {home ? (
        // Who made it and who sells it, said plainly. "A × partnership"
        // left both questions open.
        <span className="cp-mast__of">
          Built by <a href={LUMECON_URL} target="_blank" rel="noreferrer">Lumecon</a>. Available
          exclusively through{" "}
          <a href={TBN_URL} target="_blank" rel="noreferrer">Tribal Business News</a>.
        </span>
      ) : (
        <span className="cp-mast__of cp-mast__page">{page}</span>
      )}
      {user ? (
        <span className="cp-mast__user">
          {user.email}
          {" · "}
          <button type="button" className="cp-split__linkbtn" onClick={onSignOut}>
            Sign out
          </button>
        </span>
      ) : null}
    </header>
  );
}

/**
 * The way back to the hub, stated rather than implied.
 *
 * A linked wordmark is a convention people who already know the site use;
 * this is the one an arriving reader sees. It sits directly under the
 * masthead on every page below the hub, in the same clothes as the article
 * page's own back link.
 */
export function PressBack({ label = "All of Cedar Press" }) {
  return (
    <Link className="cp-ar__back cp-back" to={PRESS_PATH}>
      <span aria-hidden="true">&#8592;</span> {label}
    </Link>
  );
}

/**
 * The footer: the whole map, then who publishes it, then the promise.
 *
 * Every page carried its own footer with a different pair of links, so where
 * the footer took you depended on where you already were. It carries every
 * page now, on all of them. `deep` continues the close band's navy instead of
 * cutting back to paper for six lines of chrome.
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
          <Link to={PRESS_REQUEST_PATH}>Tribal data request</Link>
          <Link to={PRESS_RESEARCH_PATH}>Research access</Link>
          <a href="mailto:contact@lumecon.ai?subject=Cedar%20Press%20feedback">Send feedback</a>
        </nav>
        <div className="cp-foot__meta">
          <span>
            <a href={TBN_URL} target="_blank" rel="noreferrer">tribalbusinessnews.com</a>
            {" · "}
            <a href={LUMECON_URL} target="_blank" rel="noreferrer">lumecon.ai</a>
          </span>
          <span>Every collection carries its method · corrections reach every release they touch</span>
        </div>
      </div>
    </footer>
  );
}
