// Cedar Press: the articles page.
//
// The briefs' own front page, behind its door on the hub. Moved off the
// one-page reader when the hub split the surface: a front page, not a row
// of tiles — the newest brief leads at double width, the rest stack beside
// it, and growth appends to the stack with the archive living at TBN.
import "../../index.css";
import "../../styles/redesign.css";
import "../../styles/grove/press.css";
import { Link } from "react-router";

import { useAuth } from "../../context/useAuth";
import { useFadeIn } from "../../features/grove/useFadeIn";
import { LAUNCH_COLLECTION } from "../../features/grove/collection";
import { canReadCedarPress } from "../../features/grove/pressAccess";
import { AD_SLOT } from "../../features/grove/pressAds";
import { LUMECON_URL, PRESS_ARTICLES, TBN_URL } from "../../features/grove/pressArticles";
import { pressArticlePath } from "../../features/grove/pressRoutes";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { useScrollToTop } from "../../features/grove/useScrollToTop";
import { Contours } from "./pressAtmosphere";
import PressAd from "./PressAd";
import { PressCedarFab } from "./PressCedarFab";
import { PressFoot, PressMast } from "./PressChrome";
import PressGate from "./PressGate";

function ArticleCard({ article, compact = false }) {
  const dataset = LAUNCH_COLLECTION.find((item) => item.id === article.datasetId);
  const className = compact ? "cp-art cp-art--compact" : "cp-art cp-art--lead";
  const inner = (
    <>
      {/* Sector photography stands in until the real brief publishes with
          its own image. */}
      <div className="cp-art__art">
        <img className="cp-art__img" src={article.image} alt={article.imageAlt} loading="lazy" />
      </div>
      <div className="cp-art__body">
        {/* A demonstration placeholder says so on the card: the body and its
            figures are invented, and "Original research" would be a claim the
            piece cannot carry until sourced work replaces it. */}
        <span className="cp-art__tag">
          {article.kind || "Original research"}
          <b>{dataset?.name || article.tag}</b>
        </span>
        <h2 className="cp-art__title">{article.title}</h2>
        <p className="cp-art__dek">{article.dek}</p>
        <span className="cp-art__meta">
          {article.date} · from {dataset?.name}
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
  useDocumentTitle("Articles");
  const { user, loading, logout } = useAuth();
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
        <PressMast user={entitled ? user : null} onSignOut={() => logout()} section="articles" />

        {/* The page says what it is: standing alone, it cannot borrow the
            reader's hero for context the way it did as a section. */}
        <section className="cp-mh cp-fade">
          <p className="cp-hero__access">Original research</p>
          <h1 className="cp-mh__title">The Data Briefs.</h1>
          <p className="cp-mh__sub">
            Original research built from the collections and written for people who work in
            Indian Country&rsquo;s economy. Every brief names the collection behind it, and the
            data it draws on is downloadable from the same subscription.
          </p>
        </section>

        <section className="cp-surf cp-surf--paper cp-fade" id="briefs" aria-label="Latest research">
          <Contours strength={1} />
          <div className="cp-surf__in">
            <div className="cp-artgrid">
              <ArticleCard article={PRESS_ARTICLES[0]} />
              <div className="cp-artstack">
                {PRESS_ARTICLES.slice(1).map((article) => (
                  <ArticleCard key={article.id} article={article} compact />
                ))}
                <a className="cp-artmore" href={TBN_URL} target="_blank" rel="noreferrer">
                  Selected Cedar Press research also publishes with Tribal Business News →
                </a>
              </div>
            </div>
            <PressAd slot={AD_SLOT.BRIEFS} />
          </div>
        </section>

        <PressCedarFab />
        <PressFoot />
      </main>
    </div>
  );
}
