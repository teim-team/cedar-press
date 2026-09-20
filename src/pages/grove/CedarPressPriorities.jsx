// REVIEW OWNER: Havala
//
// Shape the Research: the page where a subscription spends its Cedar
// Points.
//
// Two kinds of priority, one currency. Research questions are things Cedar
// Press should investigate or publish; data priorities are things
// subscribers want Cedar to build or expand. Every priority shows its
// points AND how many subscriptions put them there, because thirty points
// from twenty-five organizations is not thirty from five. A subscriber
// puts points where they want them in whatever amounts, and takes them
// back.
//
// A request in the subscriber's own words is read against the list before
// it is sent: if it reads as an existing priority, the form offers to put a
// point there and to keep the request beside it as evidence. Both can
// happen. Cedar then sees, behind a priority, the points, the
// subscriptions, and the requests with their stated uses.
//
// Points inform; they do not decide. The page says so.
//
// Without the service the page lists the priorities with no counts and says
// the counting begins with the service; nothing here invents a number.

import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";

import { fetchRelatedPriorities, submitResearchRequest } from "../../api.js";
import { useAuth } from "../../context/useAuth";
import { canReadCedarPress } from "../../features/grove/pressAccess";
import {
  PRIORITY_TYPES,
  byType,
  pointsWord,
  published,
  related as relatedLocally,
  statusLabel,
} from "../../features/grove/pressPriorities.js";
import { usePriorities } from "../../features/grove/usePriorities.js";
import { PRESS_SETTINGS_PATH } from "../../features/grove/pressRoutes";
import { EVENT, track } from "../../features/grove/telemetry.js";
import { resolveTier } from "../../workspaceTier.js";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { useFadeIn } from "../../features/grove/useFadeIn";
import { useScrollToTop } from "../../features/grove/useScrollToTop";
import { PressCedarFab } from "./PressCedarFab";
import { PressFoot, PressMast } from "./PressChrome";
import PressGate from "./PressGate";
import { PressInfluence } from "./PressInfluence";

// The use case used to be a <select> of seven options. A subscriber writing
// what they need and then being handed seven boxes to file it under is being
// told the boxes are the real question, and the boxes were guesses. It is a
// free field now, with an example rather than a menu; the service already
// stores it as text and never validated it against a list.
const USE_PLACEHOLDER = "Underwriting a loan to a tribal enterprise, and I need the parent";

function Points({ priority, mine, canMove, onMove, busy, counted }) {
  return (
    <div className="cp-pri__points">
      {/* A row of "0 points · 0 subscribers" across eleven cards reads as a
          product nobody uses. In a build with no service those zeros are not
          measurements at all, so the row says what it is instead. */}
      <span className="cp-pri__total" data-testid="priority-total">
        {counted ? (
          <>
            <b>{pointsWord(priority.points)}</b> · {priority.subscribers} subscriber{priority.subscribers === 1 ? "" : "s"}
          </>
        ) : (
          <span className="cp-pri__uncounted">Support is counted by the Cedar Press service</span>
        )}
      </span>
      {canMove ? (
        <span className="cp-pri__mine">
          <button type="button" className="cp-pri__btn" disabled={busy || !mine} onClick={() => onMove(priority.id, -1)} aria-label={`Take one point back from ${priority.title}`}>−</button>
          <span className="cp-pri__yours">{mine ? `yours: ${mine}` : "yours: 0"}</span>
          <button type="button" className="cp-pri__btn" disabled={busy} onClick={() => onMove(priority.id, 1)} aria-label={`Put one point on ${priority.title}`}>+</button>
        </span>
      ) : null}
    </div>
  );
}

/**
 * A PRIORITY IS A ROW, NOT A CARD.
 *
 * Owner, 2026-09-20: "The priorities page is useful internally, but visually
 * it is still a grid of text cards. It should become a constrained decision
 * workspace: what Cedar is being asked to improve, why it matters, what
 * evidence is needed, and status. Fewer cards, more hierarchy."
 *
 * Eleven equal cards in a three-across grid say that eleven things are
 * equally live, which is the opposite of a priority list. As rows in one
 * ledger — the shape the rest of this product uses for anything ordered —
 * the ask and the reason lead, the status sits in its own column, and the
 * support reads as a column a reader can scan down. The controls are the
 * same controls.
 */
function Priority({ priority, mine, canMove, onMove, busy, evolvedFrom, counted }) {
  return (
    <li className={`cp-pri ${priority.status === "published" ? "is-published" : ""}`} data-testid="priority">
      <div className="cp-pri__say">
        <h3 className="cp-pri__title">{priority.title}</h3>
        <p className="cp-pri__desc">{priority.description}</p>
        {evolvedFrom ? (
          <p className="cp-set__fine">Began as the research question “{evolvedFrom.title}”: answering it needed this dataset.</p>
        ) : null}
        {priority.status === "published" && priority.published_output ? (
          <p className="cp-set__fine"><a href={priority.published_output}>See what was published <span aria-hidden="true">&#8594;</span></a></p>
        ) : null}
      </div>
      <span className={`cp-pri__status cp-pri__status--${priority.status}`}>{statusLabel(priority.status)}</span>
      <Points priority={priority} mine={mine} canMove={canMove} onMove={onMove} busy={busy} counted={counted} />
    </li>
  );
}

/**
 * The request form. As the subscriber types, the list is read against the
 * text (locally at once, by the service when connected); a match offers a
 * point on that priority and keeps the request beside it.
 */
function RequestForm({ priorities, connected, canMove, available, onDone }) {
  const [text, setText] = useState("");
  const [useCase, setUseCase] = useState("");
  // Read locally at once; the service's reading replaces it when it
  // arrives, and is dropped the moment the text changes again.
  const [serverMatches, setServerMatches] = useState(null);
  const [support, setSupport] = useState(true);
  const [sent, setSent] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const localMatches = useMemo(() => (text.trim().length < 12 ? [] : relatedLocally(text, priorities)), [text, priorities]);

  useEffect(() => {
    if (!connected || text.trim().length < 12) return undefined;
    const controller = new AbortController();
    const t = window.setTimeout(() => {
      fetchRelatedPriorities({ text, signal: controller.signal })
        .then((r) => { if (!controller.signal.aborted) setServerMatches(r.matches); })
        .catch(() => {});
    }, 300);
    return () => { controller.abort(); window.clearTimeout(t); };
  }, [text, connected]);

  const matches = serverMatches ?? localMatches;
  const best = matches[0] ?? null;
  const submit = async (event) => {
    event.preventDefault();
    if (!connected) return;
    setBusy(true);
    setError(null);
    try {
      const supportPoints = best && support && canMove && available > 0 ? 1 : 0;
      const result = await submitResearchRequest({ text, useCase, priorityId: best?.id ?? null, supportPoints });
      track(EVENT.researchRequested, { associated: Boolean(best), supported: supportPoints > 0 });
      setSent(result);
      setText("");
      onDone();
    } catch (e) {
      setError(e?.message ?? "The request was not sent.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="cp-pri__form" onSubmit={submit} data-testid="request-form">
      <label className="cp-pri__label" htmlFor="pri-text">Tell Cedar what you need</label>
      <textarea
        id="pri-text"
        className="cp-pri__text"
        rows={4}
        value={text}
        onChange={(e) => { setText(e.target.value); setServerMatches(null); setSent(null); }}
        placeholder="I wish you had a dataset showing which tribal enterprises own which subsidiaries…"
      />
      <p className="cp-pri__hint">
        Anything. A question, a dataset, a field missing from one you already use, a year Cedar
        does not reach yet, a nation whose records are thin. There is no list to choose from and
        nothing is out of scope to ask for.
      </p>
      <label className="cp-pri__label" htmlFor="pri-use">
        What you would use it for <span className="cp-pri__opt">optional</span>
      </label>
      <input
        id="pri-use"
        type="text"
        className="cp-pri__use"
        value={useCase}
        onChange={(e) => setUseCase(e.target.value)}
        placeholder={USE_PLACEHOLDER}
      />
      {best ? (
        <div className="cp-pri__match" data-testid="request-match">
          <span className="cp-set__cap">This looks related to an existing {PRIORITY_TYPES[best.type]?.label.toLowerCase()}</span>
          <p className="cp-pri__matchtitle">{best.title}</p>
          <p className="cp-set__fine">{pointsWord(best.points)} · {best.subscribers} subscriber{best.subscribers === 1 ? "" : "s"}</p>
          <label className="cp-pri__check">
            <input type="checkbox" checked={support} onChange={(e) => setSupport(e.target.checked)} disabled={!canMove || available < 1} />
            Support this priority with a point{available < 1 && canMove ? " (none available yet)" : ""}
          </label>
          <p className="cp-set__fine">Your request is kept beside it either way, in your own words.</p>
        </div>
      ) : null}
      <div className="cp-set__acts">
        <button type="submit" className="gv-btn gv-btn--primary" disabled={!connected || busy || text.trim().length < 12}>
          {best ? "Submit my specific use case" : "Submit request"}
        </button>
        {!connected ? <span className="cp-set__fine">Sending needs the Cedar Press service, which this build is not connected to.</span> : null}
      </div>
      {sent ? <p className="cp-pri__sent" role="status">Received. It shows under “Submitted by you” on your profile{sent.priority_id ? ", beside the priority it relates to" : ""}.</p> : null}
      {error ? <p className="cp-pri__error" role="alert">{error}</p> : null}
    </form>
  );
}

export default function CedarPressPriorities() {
  useDocumentTitle("Shape the research");
  const { user, loading, logout } = useAuth();
  const entitled = canReadCedarPress(user);
  const fadeRoot = useFadeIn();
  useScrollToTop("priorities");
  const tier = resolveTier(user);
  const { priorities, influence, status, error, connected, reload, move } = usePriorities({ signedIn: entitled });
  const [busy, setBusy] = useState(false);
  const [moveError, setMoveError] = useState(null);

  if (!loading && !entitled) {
    return (
      <div className="teim-rd teim-rd--paper">
        <PressGate user={user} />
      </div>
    );
  }

  const mine = Object.fromEntries((influence?.allocations ?? []).map((a) => [a.priority_id, a.points]));
  const canMove = status === "ok";
  // Whether a count on a card is a measurement rather than a placeholder.
  const counted = status === "ok";
  const available = influence?.points_available ?? 0;
  const onMove = async (id, points) => {
    setBusy(true);
    setMoveError(null);
    try {
      await move(id, points);
      track(EVENT.priorityAllocated, { points });
    } catch (e) {
      setMoveError(e?.message ?? "The points did not move.");
    } finally {
      setBusy(false);
    }
  };
  const byId = Object.fromEntries(priorities.map((p) => [p.id, p]));
  const shipped = published(priorities);

  return (
    <div className="teim-rd teim-rd--paper">
      <main id="cp-main" className="cp cp-page" ref={fadeRoot}>
        <PressMast user={entitled ? user : null} onSignOut={() => logout()} section="priorities" />

        <section className="cp-mh cp-fade">
          <p className="cp-hero__access">Shape the research</p>
          <h1 className="cp-mh__title">What should Cedar research and build next?</h1>
          {/* The points used to open this paragraph, which made the page read
              as a scoring system with a comment box attached. The owner's
              ruling is that the writing is the product: a subscriber says what
              they need, in their words, with no list to choose from. The
              points are how that gets weighted, so they come second. */}
          <p className="cp-mh__sub">
            Tell Cedar what you need in your own words. There is no list of categories and nothing
            is out of scope to ask for. Your subscription also earns Cedar Points in each month you
            use Cedar Press, and you can put those behind your own request or behind anything
            another subscriber has asked for. Priorities are considered alongside feasibility, data
            quality, research value and Cedar’s editorial judgment.
          </p>
        </section>

        <div className="cp-pri__layout cp-fade">
          <div className="cp-pri__side">
            <PressInfluence influence={influence} tier={tier} status={status} brief />
            {status === "static" ? (
              // The influence card above already says this build has no
              // service. This adds the one thing it does not: what the list
              // below is, given that.
              <p className="cp-set__fine cp-pri__note" data-testid="priorities-static">
                The priorities below are what Cedar has put forward. Support cannot be placed here.
              </p>
            ) : null}
            {status === "failed" ? <p className="cp-pri__error" role="alert">{error} <button type="button" className="cp-ex__clear" onClick={() => reload()}>Try again</button></p> : null}
            {moveError ? <p className="cp-pri__error" role="alert">{moveError}</p> : null}
            <p className="cp-set__fine">Your allocations and activity are on <Link to={PRESS_SETTINGS_PATH}>your profile</Link>.</p>
          </div>

          <div className="cp-pri__main">
            {shipped.length ? (
              <section className="cp-pri__shipped" aria-label="You asked. Cedar researched it.">
                <span className="cp-set__cap">You asked. Cedar researched it.</span>
                <ul>
                  {shipped.map((p) => (
                    <li key={p.id}>
                      <b>{p.title}</b> was one of subscribers’ priorities ({pointsWord(p.points)}, {p.subscribers} subscriber{p.subscribers === 1 ? "" : "s"}).
                      {p.published_output ? <> <a href={p.published_output}>See what was published <span aria-hidden="true">&#8594;</span></a></> : null}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            {/* THE ASK COMES FIRST.
                This sat under eleven cards, which said, structurally, "pick
                one of these". The owner's ruling is the opposite: a subscriber
                writes whatever they want and the list is what other people
                happened to write first. So the box leads and the list supports
                it. */}
            <section className="cp-pri__ask" aria-label="Ask for anything">
              <div className="cp-head">
                <span className="cp-sec__band">Ask for anything</span>
              </div>
              <p className="cp-pri__lede">
                If it reads as something another subscriber has already asked for, Cedar offers to
                put your point there and keeps your wording beside it, because the wording is the
                part that says what you actually need.
              </p>
              <div className="cp-pri__askgrid">
                <RequestForm priorities={priorities} connected={connected && entitled} canMove={canMove} available={available} onDone={() => reload()} />
                <aside className="cp-pri__what" aria-label="What happens to a request">
                  <span className="cp-set__cap">What happens to it</span>
                  <ol className="cp-pri__steps">
                    <li>
                      <b>It is read.</b> Cedar checks it against everything subscribers have already
                      asked for, so a request that has been made ten times is visibly ten requests.
                    </li>
                    <li>
                      <b>It is kept whole.</b> Your wording is stored as written and shown to Cedar
                      beside any priority it relates to. It is never reduced to a category.
                    </li>
                    <li>
                      <b>It is answered or it is not.</b> Points inform the order of the work. They
                      do not decide it, and Cedar says which priorities it took up in What&rsquo;s new.
                    </li>
                  </ol>
                </aside>
              </div>
            </section>

            {["research_question", "dataset"].map((type) => (
              <section key={type} className="cp-pri__group" aria-label={PRIORITY_TYPES[type].plural} data-testid={`priorities-${type}`}>
                <div className="cp-head">
                  <span className="cp-sec__band">{PRIORITY_TYPES[type].plural}</span>
                </div>
                <p className="cp-pri__lede">{PRIORITY_TYPES[type].lede}</p>
                <ul className="cp-pri__list">
                  {byType(priorities, type).map((p) => (
                    <Priority
                      key={p.id}
                      priority={p}
                      mine={mine[p.id] ?? 0}
                      canMove={canMove}
                      onMove={onMove}
                      busy={busy}
                      evolvedFrom={p.evolved_from ? byId[p.evolved_from] : null}
                      counted={counted}
                    />
                  ))}
                </ul>
              </section>
            ))}

          </div>
        </div>

        <PressCedarFab />
        <PressFoot />
      </main>
    </div>
  );
}
