// REVIEW OWNER: Havala
//
// The React seam over the Cedar conversation runtime (`cedarConversation.js`).
//
// One hook for both Cedar surfaces. The thread, its memory and the quick
// replies under each answer are plain values with pure transitions; this
// hook only sequences a turn: the reader's bubble, the typing indicator, the
// answer from whatever `resolve` is (the door's local bank, the reader's
// service), the pause that lets a reply read as composed, and the settle.
//
// `resolve(question, { memory, forced, signal, ...context })` returns
// `{ text, intent?, kind?, ...extra }`, or throws; a throw becomes an
// `error` turn rather than a stuck indicator. `followUpsFor(memory, reply,
// question, context)` names the quick replies, given the same context the
// resolver saw. `cancel()` abandons a turn in flight
// (the reader re-scoped mid-answer) so a late reply cannot land under the
// wrong heading; `retire()` takes the quick replies off a finished answer
// whose scope the reader has since left.
import { useCallback, useEffect, useRef, useState } from "react";

import { beginTurn, freshThread, retireFollowUps, settleTurn, thinkingPause } from "./cedarConversation.js";

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const reducedMotion = () =>
  typeof window !== "undefined" &&
  typeof window.matchMedia === "function" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export function useCedarThread({ resolve, followUpsFor, nonTopicIds, detectAudience, pause = true }) {
  const [thread, setThread] = useState(freshThread);
  const [pending, setPending] = useState(false);
  const threadRef = useRef(thread);
  const abortRef = useRef(null);

  useEffect(() => {
    threadRef.current = thread;
  }, [thread]);

  // Abandon a turn in flight when the panel unmounts.
  useEffect(() => () => abortRef.current?.abort(), []);

  const ask = useCallback(
    async (question, { echo, forced = null, ...context } = {}) => {
      const asked = String(question ?? "").trim();
      if (!asked || abortRef.current) return false;
      const controller = new AbortController();
      abortRef.current = controller;
      const memory = threadRef.current.memory;
      setThread((current) => beginTurn(current, echo ?? asked));
      setPending(true);
      const started = Date.now();
      let reply;
      try {
        reply = await resolve(asked, { memory, forced, signal: controller.signal, ...context });
      } catch (error) {
        reply = { text: "", kind: "error", error };
      }
      if (controller.signal.aborted) return false;
      if (pause) {
        await sleep(thinkingPause(reply?.text, { reducedMotion: reducedMotion(), elapsed: Date.now() - started }));
        if (controller.signal.aborted) return false;
      }
      const audience = detectAudience?.(asked) ?? null;
      setThread((current) =>
        settleTurn(current, reply ?? { text: "" }, {
          nonTopicIds,
          audience,
          followUpsFor: followUpsFor ? (memory, resolution) => followUpsFor(memory, resolution, asked, context) : null,
        }),
      );
      abortRef.current = null;
      setPending(false);
      return true;
    },
    [detectAudience, followUpsFor, nonTopicIds, pause, resolve],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setPending(false);
  }, []);

  const retire = useCallback(() => setThread((current) => retireFollowUps(current)), []);

  return { thread, pending, ask, cancel, retire };
}
