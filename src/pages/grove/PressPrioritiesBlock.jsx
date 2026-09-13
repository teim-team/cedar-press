// REVIEW OWNER: Havala
//
// The homepage's compact view of Shape the Research: the three most
// supported priorities and the door to the page; and, when something that
// began there has been published, the line that proves the loop closes.

import { Link } from "react-router";

import { pointsWord, published, sortPriorities } from "../../features/grove/pressPriorities.js";
import { usePriorities } from "../../features/grove/usePriorities.js";
import { PRESS_PRIORITIES_PATH } from "../../features/grove/pressRoutes";

export default function PressPrioritiesBlock({ signedIn }) {
  const { priorities, status } = usePriorities({ signedIn });
  const top = sortPriorities(priorities).slice(0, 3);
  const shipped = published(priorities)[0] ?? null;
  return (
    <section className="cp-prib cp-fade" aria-label="Subscriber research priorities" data-testid="priorities-block">
      <div className={`cp-prib__in${shipped ? " is-two" : ""}`}>
        <div>
          <span className="cp-sec__band">Subscriber research priorities</span>
          <ol className="cp-prib__list">
            {top.map((p) => (
              <li key={p.id}>
                <span className="cp-prib__title">{p.title}</span>
                <span className="cp-prib__points">{status === "ok" ? pointsWord(p.points) : "not yet counted"}</span>
              </li>
            ))}
          </ol>
          <Link className="cp-m__more" to={PRESS_PRIORITIES_PATH}>
            Shape the research <span aria-hidden="true">&#8594;</span>
          </Link>
        </div>
        {shipped ? (
          <div className="cp-prib__shipped">
            <span className="cp-sec__band">You asked. Cedar researched it.</span>
            <p>
              <b>{shipped.title}</b> was one of subscribers’ highest priorities.
              {shipped.published_output ? <> <a href={shipped.published_output}>See what was published <span aria-hidden="true">&#8594;</span></a></> : null}
            </p>
          </div>
        ) : null}
      </div>
    </section>
  );
}
