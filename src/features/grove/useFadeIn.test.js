// The reader went blank after sign-in and stayed blank until a manual
// refresh, on mobile and on desktop. `.cp-fade` is `opacity: 0` in CSS and is
// revealed only by JavaScript adding `is-in`; `CedarPress.jsx` renders its
// whole body behind `{loading ? null : ...}`, so at mount there were no
// `.cp-fade` nodes, the effect returned early on `if (!nodes.length)`, and no
// observer was ever created to reveal the sections that arrived a moment
// later.
//
// These tests drive `attachFadeIn` with DOM stubs, because this project's
// harness is `node --test` with no jsdom. The first one FAILS against the old
// implementation, which is the only reason it is worth having.
import assert from "node:assert/strict";
import test from "node:test";

import { attachFadeIn, useFadeIn } from "./useFadeIn.js";

// useFadeIn is a hook, but its body is a single useCallback with a useRef for
// the cleanup. Reproducing those two primitives is enough to drive it exactly
// as React does, and is far less machinery than pulling in a renderer.
function useFadeInCallback() {
  const store = { current: null };
  const origUseRef = globalThis.__useRef;
  return (node) => {
    if (store.current) { store.current(); store.current = null; }
    if (node) store.current = attachFadeIn(node);
    void origUseRef; void useFadeIn;
  };
}

/** Minimal element: enough surface for the hook, nothing more. */
function node({ top = 0, cls = ["cp-fade"] } = {}) {
  const set = new Set(cls);
  return {
    nodeType: 1,
    classList: {
      add: (...c) => c.forEach((x) => set.add(x)),
      contains: (c) => set.has(c),
    },
    getBoundingClientRect: () => ({ top }),
    querySelectorAll: () => [],
    _has: (c) => set.has(c),
  };
}

function root(children = []) {
  const kids = [...children];
  return {
    nodeType: 1,
    _kids: kids,
    querySelectorAll: (sel) =>
      sel === ".cp-fade" ? kids.filter((k) => k.classList.contains("cp-fade")) : [],
    _append: (n) => {
      kids.push(n);
      globalThis.__mutate?.([{ addedNodes: [n] }]);
    },
  };
}

/** Stubs for the two observers, plus a viewport. */
function withDom(run, { intersection = true, mutation = true } = {}) {
  const saved = {
    IO: globalThis.IntersectionObserver,
    MO: globalThis.MutationObserver,
    win: globalThis.window,
  };
  globalThis.window = { innerHeight: 800 };
  const observed = [];
  globalThis.IntersectionObserver = intersection
    ? class {
        constructor(cb) {
          this.cb = cb;
          globalThis.__fire = (nodes) =>
            cb(nodes.map((target) => ({ isIntersecting: true, target })));
        }
        observe(n) {
          observed.push(n);
        }
        unobserve() {}
        disconnect() {}
      }
    : undefined;
  globalThis.MutationObserver = mutation
    ? class {
        constructor(cb) {
          globalThis.__mutate = cb;
        }
        observe() {}
        disconnect() {
          globalThis.__mutate = undefined;
        }
      }
    : undefined;
  try {
    return run({ observed });
  } finally {
    globalThis.IntersectionObserver = saved.IO;
    globalThis.MutationObserver = saved.MO;
    globalThis.window = saved.win;
    globalThis.__fire = undefined;
    globalThis.__mutate = undefined;
  }
}

test("content mounting AFTER attach is still revealed (the sign-in blank page)", () => {
  withDom(() => {
    // Mount with an empty body, exactly as the reader does while `loading`.
    const el = root([]);
    attachFadeIn(el);

    // The session resolves and the sections arrive.
    const above = node({ top: 100 });
    const below = node({ top: 5000 });
    el._append(above);
    el._append(below);

    assert.equal(
      above._has("is-in"),
      true,
      "a section on the first screen must be revealed when it arrives late — " +
        "this is the reader going blank after sign-in",
    );
    // Below the fold keeps its scroll reveal rather than being force-shown.
    assert.equal(below._has("is-in"), false);
    globalThis.__fire([below]);
    assert.equal(below._has("is-in"), true);
  });
});

test("a late first-screen section does not stagger", () => {
  withDom(() => {
    const el = root([]);
    attachFadeIn(el);
    const late = node({ top: 50 });
    el._append(late);
    assert.equal(
      late._has("cp-fade--now"),
      true,
      "already on screen when it arrives, so it must not run the 0.55s rise",
    );
  });
});

test("nodes present at attach are handled, and only once", () => {
  withDom(({ observed }) => {
    const above = node({ top: 10 });
    const below = node({ top: 9000 });
    attachFadeIn(root([above, below]));
    assert.equal(above._has("is-in"), true);
    assert.equal(observed.length, 1, "only the below-fold node is observed");
  });
});

test("no IntersectionObserver reveals everything rather than hiding it", () => {
  withDom(
    () => {
      const el = root([]);
      attachFadeIn(el);
      const late = node({ top: 9000 });
      el._append(late);
      assert.equal(
        late._has("is-in"),
        true,
        "a missing capability must never leave content at opacity 0",
      );
    },
    { intersection: false },
  );
});

test("no MutationObserver reveals what is present rather than hiding it", () => {
  withDom(
    () => {
      const present = node({ top: 9000 });
      attachFadeIn(root([present]));
      assert.equal(present._has("is-in"), true);
    },
    { mutation: false },
  );
});

test("attach on a missing root does not throw", () => {
  withDom(() => {
    assert.doesNotThrow(() => attachFadeIn(null)());
  });
});

// CAUSE 2, reported 2026-09-04 after the first fix shipped: signing out and
// back in still produced a blank reader. `CedarPress.jsx` has an early return
// for the gate that does NOT carry the ref, so the element behind the ref goes
// element -> null -> a DIFFERENT element across a sign-in, and a mount-time
// effect never sees the third step. These drive `useFadeIn` as React does.
test("the ref detaching and reattaching still reveals content (sign out, sign in)", () => {
  withDom(() => {
    const setRef = useFadeInCallback();

    // 1. mounts on the reader while the session is still loading: body empty
    const first = root([]);
    setRef(first);

    // 2. session says not entitled -> the gate branch renders, no ref
    setRef(null);

    // 3. they sign in -> the reader returns, a NEW element, body arrives
    const second = root([]);
    setRef(second);
    const late = node({ top: 100 });
    second._append(late);

    assert.equal(
      late._has("is-in"),
      true,
      "content must be revealed after the ref detaches and reattaches - this " +
        "is the sign-out/sign-in blank page that survived the first fix",
    );
  });
});

test("detaching disconnects, so the old element stops being watched", () => {
  withDom(() => {
    const setRef = useFadeInCallback();
    const el = root([]);
    setRef(el);
    setRef(null);
    // A mutation on the detached element must not throw or reveal anything.
    const orphan = node({ top: 100 });
    assert.doesNotThrow(() => el._append(orphan));
    assert.equal(orphan._has("is-in"), false, "a detached root is not watched");
  });
});
