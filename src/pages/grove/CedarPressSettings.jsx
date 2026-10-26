// Settings: the account, the errands, and one optional question.
//
// The footer had grown to eight links because every page it could reach was
// listed in it. The three that are errands rather than reading — the tribal
// data request, research access, and contact — live here now, with the
// account, so the footer can go back to being a footer.
//
// Nothing here is required to read anything. The one question this page
// asks is asked plainly: more detail means better-curated collections, and
// a reader who does not want to answer never sees it again.
import { useCallback, useEffect, useState } from "react";
import { LUMECON_URL, contactHref } from "../../features/grove/appLink.js";
import { Link } from "react-router";

import { changePassword, fetchAccountProfile, requestEmailChange, saveAccountProfile } from "../../api";
import { useAuth } from "../../context/useAuth";
import { usePriorities } from "../../features/grove/usePriorities.js";
import { PressInfluence } from "./PressInfluence";
import { useFadeIn } from "../../features/grove/useFadeIn";
import { canReadCedarPress } from "../../features/grove/pressAccess";
import { loadWork, saveWork, workOptions } from "../../features/grove/readerWork.js";
import { PRESS_TIERS } from "../../features/grove/pressCatalog";
import { PRESS_REQUEST_PATH, PRESS_RESEARCH_PATH } from "../../features/grove/pressRoutes";
import { resolveTier } from "../../workspaceTier.js";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { useScrollToTop } from "../../features/grove/useScrollToTop";
import { PressCedarFab } from "./PressCedarFab";
import { PressFoot, PressMast } from "./PressChrome";
import PressGate from "./PressGate";
import { TierName } from "./TierName";
import { BillingCard } from "./BillingCard.jsx";
import { buildLine } from "../../features/grove/buildStamp.js";

/**
 * The one question. Optional, remembered, and stated as the trade it is:
 * telling the desk what you work on is how the collections get built for
 * the people reading them.
 */
function WorkCard() {
  const [work, setWork] = useState("");
  const [saved, setSaved] = useState(null);
  const [busy, setBusy] = useState(false);

  const apply = useCallback((value) => {
    setSaved(value);
    setWork(value ?? "");
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let live = true;
    (async () => {
      const value = await loadWork({ signal: controller.signal }).catch(() => null);
      if (live) apply(value);
    })();
    return () => {
      live = false;
      controller.abort();
    };
  }, [apply]);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      apply(await saveWork(work));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="cp-set__card cp-fade" aria-label="What you work on">
      <span className="cp-set__cap">What you work on</span>
      {/* "and whose requests carry weight" was the tail of this sentence.
          Cut per the implementation brief: it reads as though access to the
          research is bought with disclosure, which is not how the queue
          works and is a strange thing to say to someone being asked for
          their profession. */}
      <p className="cp-set__body">
        Tell us a little about your work and we can aim the collections better: it helps us
        see which ones to extend and what to write about next.
      </p>
      <form className="cp-set__form" onSubmit={submit}>
        <label className="cp-who__label" htmlFor="cp-work">
          Your work
        </label>
        <select id="cp-work" value={work} onChange={(event) => setWork(event.target.value)}>
          <option value="">Rather not say</option>
          {/* The landing audiences, plus the reader's own stored answer
              when it is a preserved one (shown under the audience it
              belongs to), so saving never drops it. */}
          {workOptions(saved).map((kind) => (
            <option key={kind.id} value={kind.id}>
              {kind.label}
            </option>
          ))}
        </select>
        <div className="cp-set__acts">
          <button type="submit" className="gv-btn gv-btn--quiet" disabled={busy || work === (saved ?? "")}>
            {busy ? "Saving" : saved ? "Update" : "Save"}
          </button>
        </div>
      </form>
    </section>
  );
}


function EmailChangeForm() {
  const [newEmail, setNewEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [sentTo, setSentTo] = useState(null);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await requestEmailChange({ newEmail, password });
      setSentTo(newEmail.trim());
      setPassword("");
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <details className="cp-set__more">
      <summary>Change email</summary>
      <form className="cp-set__form" onSubmit={submit}>
        <label className="cp-who__label" htmlFor="cp-email-new">New email</label>
        <input id="cp-email-new" type="email" autoComplete="email" maxLength={254}
          value={newEmail} onChange={(event) => setNewEmail(event.target.value)} required />
        <label className="cp-who__label" htmlFor="cp-email-password">Current password</label>
        <input id="cp-email-password" type="password" autoComplete="current-password"
          value={password} onChange={(event) => setPassword(event.target.value)} required />
        {error ? <p className="cp-gate__error" role="alert">{error}</p> : null}
        {sentTo ? (
          <p className="cp-gate__ok" role="status">
            If {sentTo} can be used, a confirmation link is on its way there. Your email changes when you open it.
          </p>
        ) : null}
        <div className="cp-set__acts">
          <button type="submit" className="gv-btn gv-btn--quiet" disabled={busy}>
            {busy ? "Sending" : "Send confirmation link"}
          </button>
        </div>
      </form>
    </details>
  );
}

function ProfileCard({ user, tier, onSignOut }) {
  const [profile, setProfile] = useState(null);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const apply = useCallback((value) => {
    setProfile(value);
    setName(value?.name ?? "");
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchAccountProfile({ signal: controller.signal }).then(apply).catch(() => {
      if (!controller.signal.aborted) setError("Your profile could not be loaded.");
    });
    return () => controller.abort();
  }, [apply]);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      apply(await saveAccountProfile({ name }));
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="cp-set__card cp-fade" aria-label="Profile">
      <span className="cp-set__cap">Profile</span>
      <form className="cp-set__form" onSubmit={submit}>
        <label className="cp-who__label" htmlFor="cp-profile-name">Name</label>
        <input id="cp-profile-name" type="text" autoComplete="name" maxLength={120}
          value={name} onChange={(event) => setName(event.target.value)} disabled={!profile} />
        {error ? <p className="cp-gate__error" role="alert">{error}</p> : null}
        <div className="cp-set__acts">
          <button type="submit" className="gv-btn gv-btn--quiet" disabled={busy || !profile || name.trim() === (profile.name ?? "")}>
            {busy ? "Saving" : "Save name"}
          </button>
        </div>
      </form>
      <dl className="cp-set__rows">
        <div>
          <dt>Email</dt>
          <dd>{user?.email}{profile?.email_verified ? " (verified)" : ""}</dd>
        </div>
        {profile?.member_since ? (
          <div>
            <dt>Member since</dt>
            <dd>{new Date(`${profile.member_since}T00:00:00`).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })}</dd>
          </div>
        ) : null}
        <div>
          <dt>Plan</dt>
          <dd>{tier ? <TierName name={tier.name} /> : "No current paid access"}</dd>
        </div>
      </dl>
      <EmailChangeForm />
      <div className="cp-set__acts">
        <button type="button" className="gv-btn gv-btn--quiet" onClick={onSignOut}>
          Sign out
        </button>
      </div>
    </section>
  );
}

function PasswordCard() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setDone(false);
    try {
      await changePassword({ currentPassword: current, newPassword: next });
      setCurrent("");
      setNext("");
      setDone(true);
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="cp-set__card cp-fade" aria-label="Password">
      <span className="cp-set__cap">Password</span>
      <p className="cp-set__body">
        Changing your password signs you out on every other device.
      </p>
      <form className="cp-set__form" onSubmit={submit}>
        <label className="cp-who__label" htmlFor="cp-pw-current">Current password</label>
        <input id="cp-pw-current" type="password" autoComplete="current-password"
          value={current} onChange={(event) => setCurrent(event.target.value)} required />
        <label className="cp-who__label" htmlFor="cp-pw-new">New password</label>
        <input id="cp-pw-new" type="password" autoComplete="new-password" minLength={10}
          placeholder="10 or more characters"
          value={next} onChange={(event) => setNext(event.target.value)} required />
        {error ? <p className="cp-gate__error" role="alert">{error}</p> : null}
        {done ? <p className="cp-gate__ok" role="status">Password changed.</p> : null}
        <div className="cp-set__acts">
          <button type="submit" className="gv-btn gv-btn--quiet" disabled={busy}>
            {busy ? "Saving" : "Change password"}
          </button>
        </div>
      </form>
    </section>
  );
}

export default function CedarPressSettings() {
  useDocumentTitle("Settings");
  const { user, loading, logout } = useAuth();
  const entitled = canReadCedarPress(user);
  useScrollToTop("settings");
  // Sitewide arrival language.
  const fadeRoot = useFadeIn();
  const { influence, status: influenceStatus } = usePriorities({ user: entitled ? user : null });

  if (!loading && !user) {
    return (
      <div className="teim-rd teim-rd--paper">
        <PressGate user={user} />
      </div>
    );
  }

  const tierId = resolveTier(user);
  const tier = PRESS_TIERS.find((entry) => entry.id === tierId);

  return (
    <div className="teim-rd teim-rd--paper">
      <main id="cp-main" className="cp cp-page" ref={fadeRoot}>
        <PressMast />

        <section className="cp-mh cp-fade">
          <p className="cp-hero__access">Settings</p>
          <h1 className="cp-mh__title">Your account.</h1>
          <p className="cp-mh__sub">
            Manage your Cedar Press access, annual subscription and preferences.
          </p>
        </section>

        {/* ACCOUNT FIRST, THEN PARTICIPATION.
            Five cards in one undifferentiated grid gave billing, a profile
            question, research influence, two public programmes and another
            product the same standing, so the page read as a pile rather than
            as an account. Two groups, each named: what this subscription IS,
            then what it TAKES PART IN. Nothing moves off the page. */}
        <h2 className="cp-set__group">Account</h2>
        <div className="cp-set cp-set--account cp-fade">
          <ProfileCard user={user} tier={tier} onSignOut={() => logout()} />
          <BillingCard />
          <PasswordCard />
          <WorkCard />
        </div>

        <h2 className="cp-set__group">Research and support</h2>
        <div className="cp-set cp-set--support cp-fade">
          {/* Where the account's influence lives: what this subscription has
              earned by using the product, where it put it, and what it asked
              for. The page is worth visiting for this, not only for billing. */}
          {entitled ? <PressInfluence influence={influence} tier={tierId} status={influenceStatus} /> : null}

          {/* Links out to public programs, not features of the account: both
              pages work with or without a subscription, and the gate and
              footer name them to non-subscribers too. This card is the
              signed-in convenience. */}
          {/* NOT A CARD, AND NOT THREE OF THEM.
              These were two more bordered panels beside the influence one,
              which put billing-adjacent links, a points ledger and a pitch
              for another product at equal visual weight, and left the two
              short ones holding a screenful of empty white. They are a list
              of places to go, so they are a list. */}
          <div className="cp-set__aside">
            <ul className="cp-set__links cp-set__links--flat">
              <li>
                <Link to={PRESS_REQUEST_PATH}>
                  <b>Tribal data request</b>
                  <span>
                    What Cedar holds about a nation, and how a government asks for it or asks it
                    to be corrected.
                  </span>
                </Link>
              </li>
              <li>
                <Link to={PRESS_RESEARCH_PATH}>
                  <b>Research access</b>
                  <span>
                    One or two collections for a defined project, for work that does not warrant a
                    subscription.
                  </span>
                </Link>
              </li>
              <li>
                <a href={contactHref("Cedar Press")}>
                  <b>Contact the research desk</b>
                  <span>
                    Corrections, questions about a method, and what the collections should cover
                    next.
                  </span>
                </a>
              </li>
            </ul>
            {/* One line, after the list. Cedar Grove is the next product up,
                not a fourth thing to manage on an account page. */}
            <p className="cp-set__beyond">
              Cedar Grove carries the same collections into the environment they were built for:
              record-level exploration, entity filters, full histories and Cedar across all of them
              at once.{" "}
              <a href={LUMECON_URL} target="_blank" rel="noreferrer">
                About Cedar Grove <span aria-hidden="true">&#8594;</span>
              </a>
            </p>
          </div>

        </div>

        {/* WHICH BUILD IS THIS. The page is served from S3 behind CloudFront,
            so "it hasn't updated" has three possible causes — the browser
            cached it, CloudFront cached it, or the publish never ran. For a
            month it was the third and nothing on the page said so. This line
            is the difference between guessing and knowing, and it is readable
            on a phone without developer tools. Quote it in any report that
            something is or is not live. */}
        <p className="cp-set__build">
          <span>Build</span>
          <code data-testid="press-build">{buildLine()}</code>
        </p>

        <PressCedarFab />
        <PressFoot />
      </main>
    </div>
  );
}
