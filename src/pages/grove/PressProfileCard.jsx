// Two questions, asked once.
//
// The subscription tells the service an email address and nothing else, so
// the shelf is curated for an audience it cannot see. This asks who is
// reading, in the terms the roadmap actually uses, and says why — a reader
// who understands what the answer is for is a reader who answers accurately.
//
// It is a card on the overview rather than a modal over it: nothing here is
// urgent enough to block a page a subscriber came to read, and a wall in
// front of the product is how surveys get answered carelessly.
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "../../context/useAuth";
import { isConnected } from "../../config.js";
import { dismissProfile, loadProfile, saveProfile } from "../../features/grove/profileStore.js";
import {
  ORGANIZATION_KINDS,
  ROLES,
  isProfileComplete,
  likelyOrganizationKind,
  organizationLabel,
} from "../../features/grove/subscriberProfile.js";
import { EVENT, identify, track, trackError } from "../../features/grove/telemetry.js";

export default function PressProfileCard() {
  const { user } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [kind, setKind] = useState("");
  const [role, setRole] = useState("");
  const [organization, setOrganization] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const apply = useCallback(
    (next) => {
      setProfile(next);
      setKind(next?.organizationKind ?? likelyOrganizationKind(user?.email) ?? "");
      setRole(next?.role ?? "");
      setOrganization(next?.organization ?? "");
      identify(user, next);
    },
    [user],
  );

  useEffect(() => {
    const controller = new AbortController();
    let live = true;
    (async () => {
      try {
        const next = await loadProfile({ signal: controller.signal });
        if (live) apply(next);
      } catch (err) {
        if (live && err?.name !== "AbortError") trackError(err, { at: "profileLoad" });
      } finally {
        if (live) setLoaded(true);
      }
    })();
    return () => {
      live = false;
      controller.abort();
    };
  }, [apply]);

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const next = await saveProfile({ organizationKind: kind, role, organization });
      apply(next);
      setEditing(false);
      track(EVENT.profileSaved, { organizationKind: next?.organizationKind, role: next?.role });
    } catch (err) {
      trackError(err, { at: "profileSave" });
      setError("That could not be saved. Try again in a moment.");
    } finally {
      setSaving(false);
    }
  };

  const putAside = async () => {
    try {
      const next = await dismissProfile(profile);
      apply(next);
      track(EVENT.profileDismissed);
    } catch (err) {
      trackError(err, { at: "profileDismiss" });
    }
  };

  if (!loaded || !user) return null;
  const complete = isProfileComplete(profile);

  // Answered and not being changed: one quiet line, with the way to change
  // it. A card that keeps asking after it has been answered is a nag.
  if (complete && !editing) {
    return (
      <p className="cp-who__done">
        <span>Reading as</span>
        <b>{profile.role}</b>
        <span>·</span>
        <b>{profile.organization || organizationLabel(profile.organizationKind)}</b>
        <button type="button" className="cp-split__linkbtn" onClick={() => setEditing(true)}>
          Change
        </button>
      </p>
    );
  }

  if (!complete && profile?.dismissed && !editing) {
    return (
      <p className="cp-who__done">
        <span>Tell us who is reading, so the shelf is built for you.</span>
        <button type="button" className="cp-split__linkbtn" onClick={() => setEditing(true)}>
          Answer two questions
        </button>
      </p>
    );
  }

  return (
    <section className="cp-sec cp-who" aria-label="Who is reading">
      <span className="cp-sec__band">Who is reading</span>
      <div className="cp-who__in">
        <div>
          <h2 className="cp-cedar__title">Which seat are you in?</h2>
          <p className="cp-who__lede">
            A subscription tells us an address, which does not say whether the collections are
            being read by a tribal council, a lender's underwriter or a newsroom. Two answers
            decide what gets built next — which collections get extended, which get a brief, and
            which requests carry weight.
          </p>
          <p className="cp-who__fine">
            {isConnected()
              ? "Kept with your subscription and used to shape the roadmap. It is not shared with advertisers, and it is not sent to anyone to look you up."
              : "This deployment is not connected to the platform, so answers stay in this browser and are not saved to an account."}
          </p>
        </div>
        <form className="cp-who__form" onSubmit={submit}>
          <label className="cp-who__label" htmlFor="cp-who-kind">
            Your organization
          </label>
          <select
            id="cp-who-kind"
            value={kind}
            onChange={(event) => setKind(event.target.value)}
            required
          >
            <option value="">Select one</option>
            {ORGANIZATION_KINDS.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>

          <label className="cp-who__label" htmlFor="cp-who-role">
            Your role
          </label>
          <select
            id="cp-who-role"
            value={role}
            onChange={(event) => setRole(event.target.value)}
            required
          >
            <option value="">Select one</option>
            {ROLES.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>

          <label className="cp-who__label" htmlFor="cp-who-org">
            Organization name <span className="cp-who__opt">optional</span>
          </label>
          <input
            id="cp-who-org"
            type="text"
            value={organization}
            maxLength={120}
            placeholder="So a request can be attributed"
            onChange={(event) => setOrganization(event.target.value)}
          />

          {error ? <p className="cp-gate__error" role="alert">{error}</p> : null}
          <div className="cp-who__acts">
            <button type="submit" className="gv-btn gv-btn--primary" disabled={saving}>
              {saving ? "Saving" : "Save"}
            </button>
            <button type="button" className="cp-split__linkbtn" onClick={editing ? () => setEditing(false) : putAside}>
              {editing ? "Cancel" : "Not now"}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
