// Cedar Press: the articles page.
//
// The briefs' own front page, behind its door on the hub. Moved off the
// one-page reader when the hub split the surface: a front page, not a row
// of tiles — the newest brief leads at double width, the rest stack beside
// it, and growth appends to the stack with the archive living at TBN.
import { toneClass } from "../../features/grove/duotone.js";
import { Link } from "react-router";

import { useAuth } from "../../context/useAuth";
import { useFadeIn } from "../../features/grove/useFadeIn";
import { LAUNCH_COLLECTION } from "../../features/grove/collection";
import { canReadCedarPress } from "../../features/grove/pressAccess";
import { AD_SLOT } from "../../features/grove/pressAds";
import {
  ARTICLE_IMAGE,
  LUMECON_URL,
  TBN_URL,
} from "../../features/grove/pressArticles";
import { pressArticlePath } from "../../features/grove/pressRoutes";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { useScrollToTop } from "../../features/grove/useScrollToTop";
import { Contours } from "./pressAtmosphere";
import PressAd from "./PressAd";
import { PressCedarFab } from "./PressCedarFab";
import { PressFoot, PressMast } from "./PressChrome";
import PressGate from "./PressGate";
import { useProtectedArticles } from "../../features/grove/useProtectedArticles.js";

function ArticleCard({ article }) {
  const dataset = LAUNCH_COLLECTION.find((item) => item.id === article.datasetId);
  // One square card per brief, all alike (owner, 2026-09-27: "a menu of
  // cards, like squares you can click on").
  const className = "cp-art cp-art--square";
  const inner = (
    <>
      {/* Sector photography stands in until the real brief publishes with
          its own image.

          `width`/`height` are the intrinsic pixels of the lane images (all
          1500×600), not a size: the CSS still lays the picture out at
          `width: 100%`. What they buy is the aspect ratio BEFORE the bytes
          arrive, so the card is its final height from the first layout. It
          was measured without them: the lead card's body was laid out at
          y=446 and moved to y=783 when the picture landed — a 337px jump,
          and 0.051 of the 0.052 CLS this page recorded. */}
      <div className="cp-art__art">
        <img
          className={`cp-art__img ${toneClass(article.tone)}`}
          src={article.image}
          alt={article.imageAlt}
          width={ARTICLE_IMAGE.width}
          height={ARTICLE_IMAGE.height}
          loading="lazy"
        />
      </div>
      <div className="cp-art__body">
        {/* A demonstration placeholder says so on the card: the body and its
            figures are invented, and "Original research" would be a claim the
            piece cannot carry until sourced work replaces it. */}
        <span className="cp-art__tag">
          {article.demonstration ? "Demonstration" : article.earlyAccess ? "Early access" : article.kind || "Original research"}
          <b>{dataset?.name || article.tag}</b>
        </span>
        <h2 className="cp-art__title">{article.title}</h2>
        <span className="cp-art__meta">
          {/* The collection is already named in the tag above. */}
          {article.date}
          {article.hosted ? null : " · on Tribal Business News"}
        </span>
      </div>
    </>
  );

  // A hosted piece opens here, beside its data and its rail. One that
  // publishes on Tribal Business News opens there, in a new tab, and the meta
  // line above says so before the click rather than after it.
  return article.hosted ? (
    <Link className={className} to={pressArticlePath(article.id)}>{inner}</Link>
  ) : (
    <a className={className} href={article.href} target="_blank" rel="noreferrer">
      {inner}
    </a>
  );
}

export default function CedarPressArticles() {
  useDocumentTitle("Research Briefs");
  const { user, loading } = useAuth();
  const articleState = useProtectedArticles(loading ? null : user);
  // Sitewide arrival language.
  const fadeRoot = useFadeIn();
  const entitled = canReadCedarPress(user);
  useScrollToTop("articles");
  if (!loading && !entitled) {
    return (
      <div className="teim-rd teim-rd--paper">
        <PressGate user={user} />
      </div>
    );
  }
  return (
    <div className="teim-rd teim-rd--paper">
      <main id="cp-main" className="cp cp-page" ref={fadeRoot}>
        <PressMast section="articles" />

        {/* The page says what it is: standing alone, it cannot borrow the
            reader's hero for context the way it did as a section. */}
        <section className="cp-mh cp-fade">
          <p className="cp-hero__access">Original research</p>
          <h1 className="cp-mh__title">Research Briefs.</h1>
          <p className="cp-mh__sub">
            Cedar Press research briefs use the collections to examine changes in funding,
            business activity, policy and institutions across Indian Country. Every brief names
            the records behind it, and subscribers can inspect and download the same underlying
            data. The briefs are examples of the kinds of questions the collections can answer,
            not a substitute for working with the data directly.
          </p>
        </section>

        <section className="cp-surf cp-surf--paper cp-fade" id="briefs" aria-label="Latest research">
          <Contours strength={1} />
          <div className="cp-surf__in">
            {articleState.status === "loading" ? <p role="status">Loading articles…</p> : null}
            {articleState.status === "unavailable" ? (
              <p role="status">Articles are unavailable on this connection. Your sign-in is unchanged. Please try again when the article service is available.</p>
            ) : null}
            <ul className="cp-briefgrid">
              {(articleState.data?.articles ?? []).map((article) => (
                <li key={article.id}>
                  <ArticleCard article={article} />
                </li>
              ))}
            </ul>
            <a className="cp-artmore" href={TBN_URL} target="_blank" rel="noreferrer">
              Selected Cedar Press research also publishes with Tribal Business News →
            </a>
            <PressAd slot={AD_SLOT.BRIEFS} />
          </div>
        </section>

        <PressCedarFab />
        <PressFoot />
      </main>
    </div>
  );
}
