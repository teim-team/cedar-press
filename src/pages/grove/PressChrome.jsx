// The chrome the reader's pages share: the masthead that says who made this
// and who is signed in, and the footer that carries the satellite routes.
// One component each, because the hub split the reader across three pages
// (home, articles, data) and three copies of a masthead drift three ways.
import { Link } from "react-router";

import { LUMECON_URL, TBN_URL } from "../../features/grove/pressArticles";
import {
  PRESS_METHODS_PATH,
  PRESS_PATH,
  PRESS_REQUEST_PATH,
  PRESS_RESEARCH_PATH,
  PRESS_WHATS_NEW_PATH,
} from "../../features/grove/pressRoutes";

/**
 * The masthead. `home` renders the wordmark as text (you are here); the
 * other pages link it back to the hub.
 */
export function PressMast({ user, onSignOut, home = false }) {
  return (
    <header className="cp-mast">
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

/** The footer. `deep` continues the close band's navy instead of paper. */
export function PressFoot({ deep = false }) {
  return (
    <footer className={`cp-foot${deep ? " cp-foot--deep" : ""}`}>
      <div className="cp-foot__in">
        <span>
          <Link to={PRESS_METHODS_PATH}>Methods</Link>
          {" · "}
          <Link to={PRESS_REQUEST_PATH}>Tribal data request</Link>
          {" · "}
          <Link to={PRESS_RESEARCH_PATH}>Research access</Link>
          {" · "}
          <Link to={PRESS_WHATS_NEW_PATH}>What&rsquo;s new</Link>
        </span>
        <span>
          <a href={TBN_URL} target="_blank" rel="noreferrer">tribalbusinessnews.com</a>
          {" · "}
          <a href={LUMECON_URL} target="_blank" rel="noreferrer">lumecon.ai</a>
        </span>
        <span>Every collection carries its method · corrections reach every release they touch</span>
      </div>
    </footer>
  );
}
