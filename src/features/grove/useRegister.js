// The entity register the door's preview names rows from, loaded once.
//
// Or the empty one: a row still names its entity from its own columns when
// the register cannot be read (`rowEntities`), so the preview degrades to
// names without types rather than to nothing.
import { useEffect, useState } from "react";

import { EMPTY_REGISTER, buildRegister } from "./explore.js";

export const REGISTER_PATH = "/data/cedar/register.json";

export function useRegister() {
  const [register, setRegister] = useState(EMPTY_REGISTER);
  useEffect(() => {
    let live = true;
    fetch(REGISTER_PATH)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((json) => { if (live) setRegister(buildRegister(json)); })
      .catch(() => {});
    return () => { live = false; };
  }, []);
  return register;
}
