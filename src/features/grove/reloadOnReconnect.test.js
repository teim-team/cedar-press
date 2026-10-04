// A page whose code did not arrive reloads once when the connection returns
// (reloadOnReconnect.js, used by PageBoundary.jsx).
import assert from "node:assert/strict";
import test from "node:test";

import { reloadOnceWhenOnline } from "./reloadOnReconnect.js";

test("reloads on the first online event, and only once", () => {
  const target = new EventTarget();
  let reloads = 0;
  reloadOnceWhenOnline({ target, reload: () => { reloads += 1; } });
  target.dispatchEvent(new Event("offline"));
  assert.equal(reloads, 0, "going offline is not a reason to reload");
  target.dispatchEvent(new Event("online"));
  target.dispatchEvent(new Event("online"));
  assert.equal(reloads, 1);
});

test("an unsubscribed boundary never reloads", () => {
  const target = new EventTarget();
  let reloads = 0;
  const stop = reloadOnceWhenOnline({ target, reload: () => { reloads += 1; } });
  stop();
  target.dispatchEvent(new Event("online"));
  assert.equal(reloads, 0);
});

test("the default reload is the target's own location.reload", () => {
  const target = new EventTarget();
  let reloaded = false;
  target.location = { reload: () => { reloaded = true; } };
  reloadOnceWhenOnline({ target });
  target.dispatchEvent(new Event("online"));
  assert.equal(reloaded, true);
});

test("no window (Node, prerender) is a no-op", () => {
  assert.doesNotThrow(() => reloadOnceWhenOnline({ target: undefined })());
});
