// REVIEW OWNER: Havala
//
// "Your research influence": what this subscription has and has done, the
// way the profile shows it and the Priorities page repeats it in brief.
// Everything on it is read from the service's ledger; when there is no
// service, it states the rule and says the counting has not begun.

import { Link } from "react-router";

import {
  EXPIRY_MONTHS,
  POINTS_PER_ACTIVE_MONTH,
  describeActivity,
  earningLine,
  formatMonth,
  pointsWord,
  statusLabel,
} from "../../features/grove/pressPriorities.js";
import { PRESS_PRIORITIES_PATH } from "../../features/grove/pressRoutes.js";
import { PRESS_TIERS } from "../../features/grove/pressCatalog.js";
import { TierName } from "./TierName";

function tierName(tier) {
  return PRESS_TIERS.find((t) => t.id === tier)?.name ?? "Cedar Press";
}

/**
 * The card. `influence` is the service's answer or null; `tier` is the
 * signed-in plan; `status` says whether the service answered, is absent,
 * or failed, so the card never shows a zero that means "unknown".
 */
export function PressInfluence({ influence, tier, status, brief = false }) {
  const rate = POINTS_PER_ACTIVE_MONTH[tier] ?? 0;
  return (
    <section className="cp-set__card cp-inf" aria-label="Your research influence" data-testid="influence">
      <span className="cp-set__cap">Your research influence</span>
      <p className="cp-inf__tier"><TierName name={tierName(tier)} /></p>
      {influence ? (
        <>
          <p className="cp-inf__points" data-testid="influence-points">
            <b>{pointsWord(influence.points_available)}</b> available
          </p>
          <p className="cp-inf__next">
            {influence.credited_this_month
              ? `+${influence.next_credit.points} next active month (${formatMonth(influence.next_credit.month)})`
              : `+${influence.next_credit.points} this month, on your first visit`}
          </p>
        </>
      ) : status === "static" ? (
        <p className="cp-inf__note">
          This build is not connected to the Cedar Press service, which keeps the ledger. Points are
          counted there; nothing is counted here.
        </p>
      ) : status === "failed" ? (
        <p className="cp-inf__note">The service did not answer; your points are unchanged and will show when it does.</p>
      ) : (
        <p className="cp-inf__note">Reading your ledger…</p>
      )}
      <p className="cp-set__body">{earningLine(tier)}{rate ? ` Unspent points expire after ${EXPIRY_MONTHS} months.` : ""}</p>

      {influence && !brief ? (
        <>
          <h4 className="cp-inf__h">Your priorities</h4>
          {influence.allocations.length ? (
            <table className="cp-inf__table">
              <tbody>
                {influence.allocations.map((a) => (
                  <tr key={a.priority_id}>
                    <td>{a.title}<small> · {statusLabel(a.status)}</small></td>
                    <td className="cp-inf__n">{a.points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="cp-set__fine">No points allocated yet.</p>
          )}

          <h4 className="cp-inf__h">Point activity</h4>
          {influence.activity.length ? (
            <ul className="cp-inf__activity">
              {influence.activity.map((e, i) => (
                <li key={i}><span className="cp-inf__month">{formatMonth(e.month) || e.at?.slice(0, 10)}</span> · {describeActivity(e)}</li>
              ))}
            </ul>
          ) : (
            <p className="cp-set__fine">Your first active month credits on your first visit.</p>
          )}

          <h4 className="cp-inf__h">Submitted by you</h4>
          {influence.requests.length ? (
            <ul className="cp-inf__requests">
              {influence.requests.map((r) => (
                <li key={r.id}>
                  <span className="cp-inf__reqtext">{r.text}</span>
                  <small>{r.title ? `Associated with “${r.title}” · ` : ""}{statusLabel(r.status) === r.status ? r.status.replace(/_/g, " ") : statusLabel(r.status)}</small>
                </li>
              ))}
            </ul>
          ) : (
            <p className="cp-set__fine">No requests yet.</p>
          )}
        </>
      ) : null}

      <p className="cp-set__fine cp-inf__foot">
        Subscriber priorities are considered alongside feasibility, data quality, research value and
        Cedar’s editorial judgment.{" "}
        <Link to={PRESS_PRIORITIES_PATH}>Shape the research <span aria-hidden="true">&#8594;</span></Link>
      </p>
    </section>
  );
}
