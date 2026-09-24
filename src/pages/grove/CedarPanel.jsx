// REVIEW OWNER: Havala
//
// The Ask Cedar panel, once. The door (`PressDoorCedar`) and the reader
// (`PressCedarFab`) both render this: the teal identity band with a status
// dot, the transcript of bubbles with the mark beside Cedar's, quick replies
// inside the transcript, a single-line composer with a round send, and one
// line of expectation-setting under it. It is lumecon.ai's panel
// (`src/components/CedarChat.astro` there) class for class in this app's
// register, sized to its measured width and height (see `.cp-dc__panel` in
// `styles/grove/press.css`), so a reader who meets Cedar on the site, on the
// door and behind the paywall meets one thing.
//
// What differs between the two surfaces rides in through props: the context
// line, the welcome, a line above the thread (the reader's scope), what a
// starter or a quick reply does when tapped, and `renderTurn`, which is how
// the reader's panel puts a basis line under an answer and the door puts its
// route links under one. The conversation itself is `useCedarThread`.
import { useEffect, useRef } from "react";

import { EXPECTATION_LINE } from "../../features/grove/cedarConversation.js";

const MARK = "/brand/lumecon-logo-mark-teal.png";

function Mark() {
  return (
    <span className="cp-dc__avatar" aria-hidden="true">
      <img src={MARK} alt="" width="30" height="30" />
    </span>
  );
}

/** A bot bubble's default body: paragraphs, split on blank lines. */
export function Paragraphs({ text }) {
  return String(text ?? "")
    .split("\n\n")
    .filter(Boolean)
    .map((para, i) => <p key={i}>{para}</p>);
}

/**
 * Props:
 *   contextLine     the header's second line ("Cedar Press · ...")
 *   welcome         the first bubble's body (a node)
 *   aboveThread     an optional node between the welcome and the turns
 *   starters        `[{ label, onSelect }]`, shown only on an empty thread
 *   thread          `{ turns, followUps }` from `useCedarThread`
 *   pending         whether Cedar is composing
 *   followUps       `[{ label, onSelect }]`, under the last answer
 *   renderTurn      `(turn) => node` for a bot turn's body; defaults to paragraphs
 *   asked, onAsked  the composer's value and change handler
 *   onSubmit        the composer's submit, given the trimmed question
 *   placeholder     the composer's placeholder
 *   inputDisabled   the composer cannot be used (the reader is disconnected)
 *   onClose         the close button
 *   panelRef, inputRef  refs the owner needs for focus and outside-click
 *   closeLabel      the close button's accessible name
 */
export function CedarPanel({
  contextLine,
  welcome,
  aboveThread = null,
  starters = [],
  thread,
  pending = false,
  followUps = [],
  renderTurn,
  asked,
  onAsked,
  onSubmit,
  placeholder = "Ask Cedar a question",
  inputDisabled = false,
  onClose,
  panelRef,
  inputRef,
  closeLabel = "Close Ask Cedar",
}) {
  const endRef = useRef(null);

  // A new turn scrolls into view inside the panel, never the page.
  useEffect(() => {
    if (thread.turns.length || pending) endRef.current?.scrollIntoView({ block: "nearest" });
  }, [thread, pending]);

  const submit = (event) => {
    event.preventDefault();
    const question = String(asked ?? "").trim();
    if (!question) return;
    onSubmit(question);
  };

  const body = (item) => (renderTurn ? renderTurn(item) : <Paragraphs text={item.text} />);

  return (
    <section className="cp-dc__panel" ref={panelRef} role="dialog" aria-label="Ask Cedar">
      {/* The identity band the app, the door and lumecon.ai all use: status
          dot, uppercase title, context line, all white on the one teal that
          carries white text. */}
      <header className="cp-dc__head">
        <span className="cp-dc__heading">
          <span className="cp-dc__titlerow">
            <span className="cp-dc__statusdot" aria-hidden="true" />
            <span className="cp-dc__title">Ask Cedar</span>
            <span className="cp-badge__sr">Online</span>
          </span>
          <span className="cp-dc__context">{contextLine}</span>
        </span>
        <button type="button" className="cp-dc__close" onClick={onClose} aria-label={closeLabel}>
          <span aria-hidden="true">&times;</span>
        </button>
      </header>

      <div className="cp-dc__thread" role="log" aria-live="polite" aria-busy={pending}>
        <div className="cp-dc__msg cp-dc__msg--bot">
          <Mark />
          <div className="cp-dc__bubble">{welcome}</div>
        </div>

        {aboveThread}

        {/* The starter stack belongs to the empty panel. Once a question has
            been asked it is gone, and the next questions ride under the last
            answer instead of the whole stack re-printing like a toolbar. */}
        {starters.length && !thread.turns.length ? (
          <div className="cp-dc__quickreply">
            {starters.map((starter) => (
              <button type="button" key={starter.label} className="cp-dc__chip" onClick={starter.onSelect}>
                {starter.label}
              </button>
            ))}
          </div>
        ) : null}

        {thread.turns.map((item) =>
          item.role === "you" ? (
            <div className="cp-dc__msg cp-dc__msg--you" key={item.key}>
              <div className="cp-dc__bubble">
                <p>{item.text}</p>
              </div>
            </div>
          ) : (
            <div className="cp-dc__msg cp-dc__msg--bot" key={item.key}>
              <Mark />
              <div className="cp-dc__bubble">{body(item)}</div>
            </div>
          ),
        )}

        {pending ? (
          <div className="cp-dc__msg cp-dc__msg--bot" aria-hidden="true">
            <Mark />
            <div className="cp-dc__bubble cp-dc__bubble--typing">
              <span className="cp-dc__dot" />
              <span className="cp-dc__dot" />
              <span className="cp-dc__dot" />
            </div>
          </div>
        ) : null}

        {/* The next questions, under the answer they follow, as the reader's
            own possible next turn. At most three; they are replaced by the
            next answer's own row rather than piling up. */}
        {followUps.length && !pending ? (
          <div className="cp-dc__followups" role="group" aria-label="Suggested next questions">
            {followUps.map((next) => (
              <button type="button" key={next.label} className="cp-dc__follow" onClick={next.onSelect}>
                {next.label}
              </button>
            ))}
          </div>
        ) : null}
        <div ref={endRef} />
      </div>

      <form className="cp-dc__form" onSubmit={submit} autoComplete="off">
        <label className="cp-dc__inputwrap">
          <span className="cp-badge__sr">Ask Cedar a question</span>
          <input
            ref={inputRef}
            className="cp-dc__input"
            type="text"
            value={asked}
            disabled={inputDisabled}
            placeholder={placeholder}
            maxLength={280}
            autoCorrect="off"
            autoCapitalize="sentences"
            enterKeyHint="send"
            onChange={(event) => onAsked(event.target.value)}
          />
        </label>
        <button
          type="submit"
          className="cp-dc__send"
          disabled={!String(asked ?? "").trim() || pending || inputDisabled}
          aria-label="Send"
        >
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M4 12h15M13 6l6 6-6 6" />
          </svg>
        </button>
      </form>
      {/* The one line of expectation-setting the panel owes its reader, in
          the same place and to the same effect as lumecon.ai's. It sets an
          expectation; it does not describe the machinery. */}
      <p className="cp-dc__disclaimer">{EXPECTATION_LINE}</p>
    </section>
  );
}
