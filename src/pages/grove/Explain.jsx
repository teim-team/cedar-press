// REVIEW OWNER: Havala
//
// The question mark, and what comes out of it.
//
// The owner's ask, 2026-09-13: "add question marks that you can click on or
// hover over that give a tooltip for more information throughout Cedar Press.
// Every dataset has its own nuance of technicalities. On mobile, maybe it's a
// click, unclick."
//
// So: one control, two behaviours, decided by the pointer rather than by the
// screen width. A mouse hovers and it opens; a thumb taps and it stays open
// until it is dismissed. Both get keyboard focus and Escape.
//
// WHY THIS IS NOT `title=""`
// The native tooltip cannot be styled, cannot hold a paragraph, takes about a
// second to appear, never appears on touch at all, and is announced
// inconsistently. It is the right answer for four words and the wrong one for
// a technicality about a dataset.
//
// WHAT IT MAY NOT HOLD
// Anything invented. Every panel on the site is passed prose the product
// already declares: a collection's `method`, `sources` or `limits`, a
// `link_statuses` definition, the coverage measurement. If a fact is worth a
// question mark it is worth being in a module a test can read.
//
// ACCESSIBILITY
// It is a disclosure, not a `role="tooltip"`: the content is real prose a
// reader may want to select and it can carry a link, and a tooltip that a
// screen reader announces on focus would read the whole paragraph before the
// label it belongs to. `aria-expanded` plus `aria-controls` says what it is.

import { useCallback, useEffect, useId, useRef, useState } from "react";

/** Whether this pointer hovers. Re-read on change: a tablet with a mouse
 *  attached mid-session is a real thing, and so is unplugging it. */
function useHoverPointer() {
  const [hover, setHover] = useState(() =>
    typeof window !== "undefined" && typeof window.matchMedia === "function"
      ? window.matchMedia("(hover: hover) and (pointer: fine)").matches
      : true,
  );
  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return undefined;
    const query = window.matchMedia("(hover: hover) and (pointer: fine)");
    const onChange = (event) => setHover(event.matches);
    query.addEventListener?.("change", onChange);
    return () => query.removeEventListener?.("change", onChange);
  }, []);
  return hover;
}

/**
 * `label` is what the panel is about, for a screen reader: "more about
 * Federal Prime Contracting", never "more information". `children` is the
 * panel's content. The panel flips its own edge when it would leave the
 * viewport, measured on open, so there is nothing to pass.
 */
export default function Explain({ label, children }) {
  const [open, setOpen] = useState(false);
  const [flip, setFlip] = useState(false);
  const hoverPointer = useHoverPointer();
  const id = useId();
  const wrapRef = useRef(null);
  const panelRef = useRef(null);
  // A tap fires pointerdown then, on some browsers, a synthetic mouseenter.
  // Without this the panel opened on the tap and closed on the mouseenter.
  const tapped = useRef(false);
  // And a tap also FOCUSES the button, so `onFocus` fired straight after
  // `onPointerDown` and re-opened a panel the second tap had just closed.
  // Measured on a 390px touch context: first tap opened, second tap did
  // nothing. `onFocus` is for the keyboard, so it now asks whether a pointer
  // put the focus there.
  const fromPointer = useRef(false);

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => { if (event.key === "Escape") { close(); wrapRef.current?.querySelector("button")?.focus(); } };
    const onDown = (event) => { if (!wrapRef.current?.contains(event.target)) close(); };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown);
    };
  }, [open, close]);

  // Keep the panel on screen. Measured on open, because the button's position
  // depends on where the text it annotates wrapped.
  useEffect(() => {
    if (!open) return;
    const panel = panelRef.current;
    if (!panel) return;
    setFlip(false);
    const room = document.documentElement.clientWidth;
    const box = panel.getBoundingClientRect();
    if (box.right > room - 8) setFlip(true);
  }, [open]);

  // `tapped` is read inside the handlers and never during render: a tap fires
  // pointerdown and then, on some browsers, a synthetic mouseenter, and
  // without the latch the panel opened on the tap and closed a frame later.
  return (
    <span
      className="cp-ex1"
      ref={wrapRef}
      onMouseEnter={hoverPointer ? () => { if (!tapped.current) setOpen(true); } : undefined}
      onMouseLeave={hoverPointer ? () => { if (!tapped.current) setOpen(false); } : undefined}
    >
      <button
        type="button"
        className={`cp-ex1__btn${open ? " is-open" : ""}`}
        aria-expanded={open}
        aria-controls={id}
        onPointerDown={(event) => {
          fromPointer.current = true;
          // Touch and pen latch; a mouse leaves hover in charge.
          if (event.pointerType === "mouse") return;
          tapped.current = true;
          setOpen((was) => !was);
        }}
        onClick={(event) => {
          // Keyboard activation arrives as a click with no pointer, and that
          // is the only click this handles. A mouse click was closing a panel
          // the pointer was still hovering, which then reopened the moment
          // the mouse moved a pixel; hover governs the mouse, start to end.
          // Touch is already handled in onPointerDown.
          if (event.detail === 0) setOpen((was) => !was);
        }}
        onFocus={() => {
          // A pointer already decided: a tap toggled it, a mouse is hovering
          // it. Only a keyboard arriving here should open it.
          if (fromPointer.current) { fromPointer.current = false; return; }
          setOpen(true);
        }}
        onBlur={(event) => {
          fromPointer.current = false;
          if (!wrapRef.current?.contains(event.relatedTarget)) {
            tapped.current = false;
            setOpen(false);
          }
        }}
      >
        <span aria-hidden="true">?</span>
        <span className="cp-badge__sr">{open ? "Hide" : "Show"} more about {label}</span>
      </button>
      <span
        id={id}
        ref={panelRef}
        className={`cp-ex1__panel${open ? " is-open" : ""}${flip ? " is-flipped" : ""}`}
        hidden={!open}
      >
        {children}
        {/* Under 560px the panel is a bottom sheet, and the question mark
            that opened it has usually scrolled behind it. Tapping outside
            already closes it, but a sheet with no visible way out reads as
            stuck. Hidden on a pointer that hovers, where leaving does it. */}
        <button type="button" className="cp-ex1__done" onClick={close}>Close</button>
      </span>
    </span>
  );
}
