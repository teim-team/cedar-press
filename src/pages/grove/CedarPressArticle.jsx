// REVIEW OWNER: Havala
//
// A hosted article.
//
// Research published on Cedar Press rather than on Tribal Business News.
// Both are worth doing and they do different jobs: a piece on TBN brings
// somebody to the product, and a piece here is read by somebody who already
// has it, beside the data it came from.
//
// THREE THINGS THIS PAGE CAN DO THAT THE TBN VERSION CANNOT
//
// It carries a rail, so it carries sponsorship that sits beside the text
// instead of interrupting it. It is also the only surface where an advertiser
// can buy a subject: federal contracting and gaming are different buyers, and
// the article names its own collections.
//
// It ends on the data. Every piece declares the collections behind it, and
// the block at the foot resolves each one against the reader's entitlement:
// download it if their tier opens it, and see what opens it if not. That is
// the most honest upgrade prompt in the product, because the reader has just
// read the thing the data produced.
//
// It says where the figures were made. Every chart in these pieces is built
// in Cedar Grove, and a caption that says so, next to an invitation to make
// your own, is the strongest case Grove has. Nothing here draws a decorative
// chart: a figure is its caption, its source and its provenance, because a
// chart nobody can interrogate is the fake dashboard this product avoids.

import { useEffect } from "react";
import { Link, useParams } from "react-router";

import "../../index.css";
import "../../styles/redesign.css";
import "../../styles/grove/press.css";

import { useAuth } from "../../context/useAuth";
import { useFadeIn } from "../../features/grove/useFadeIn";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { EVENT, track } from "../../features/grove/telemetry.js";
import { PressBack, PressFoot, PressMast } from "./PressChrome";
import { PRESS_FIGURES } from "../../components/grove/pressFigures";
import { AD_SLOT } from "../../features/grove/pressAds";
import { BLOCK, LUMECON_URL, PRESS_ARTICLES, TBN_URL } from "../../features/grove/pressArticles";
import { canOpenDataset, canReadCedarPress, upgradeFor } from "../../features/grove/pressAccess";
import PressGate from "./PressGate";
import { downloadCsv, hasReleaseFile } from "../../features/grove/pressDownload";
import { PRESS_CATALOG_BY_ID, groupOf } from "../../features/grove/pressCatalog";
import { formatUpdated, releaseFor } from "../../features/grove/pressReleases";
import {
  PRESS_ARTICLES_PATH,
  PRESS_DATA_PATH,
  PRESS_METHODS_PATH,
  PRESS_PATH,
} from "../../features/grove/pressRoutes";
import { useScrollToTop } from "../../features/grove/useScrollToTop";
import PressAd from "./PressAd";
import { PressCedarFab } from "./PressCedarFab";
import { TierName } from "./TierName";

const BY_ID = Object.fromEntries(PRESS_ARTICLES.map((article) => [article.id, article]));

/**
 * A figure: the chart, what it shows, what it came from, where it was made,
 * and the assumptions a reader needs to argue with it.
 *
 * The mark comes from the figure rather than from the collection, because the
 * mark is chosen from the question the sentence beside it is asking. Cedar
 * Grove holds a narrower vocabulary on purpose; the reasoning for the two
 * sitting apart is in features/grove/pressCharts.js.
 *
 * The notes are not optional and the test enforces it. A chart is a claim,
 * and a claim without its assumptions is an assertion. What is counted, what
 * is excluded, and any choice that changes the shape all belong under the
 * picture where somebody about to cite it will look.
 *
 * Every chart here is built in Cedar Grove, and saying so beside an
 * invitation to build one is the strongest case Grove has.
 */
function Figure({ block }) {
  const entry = PRESS_CATALOG_BY_ID[block.source];
  const release = releaseFor(block.source);
  const Chart = PRESS_FIGURES[block.chart];
  return (
    <figure className="cp-ar__fig">
      <figcaption className="cp-ar__figcap">{block.caption}</figcaption>
      {Chart ? (
        <div className="cp-ar__chart">
          <Chart points={block.points} series={block.series} flows={block.flows} />
        </div>
      ) : null}
      {block.notes?.length ? (
        <ul className="cp-ar__fignotes">
          {block.notes.map((note) => <li key={note}>{note}</li>)}
        </ul>
      ) : null}
      <p className="cp-ar__figsrc">
        {/* A date, never a version: the collections update continuously and
            the date is what makes the figure reproducible. */}
        <b>{entry?.name ?? block.source}</b>
        {release ? `, as of ${formatUpdated(release.updated)}` : null}
        . Built in Cedar Grove.{" "}
        {/* To the Grove section on the reader, not /app/grove: a Press
            reader clicking this has no Grove entitlement, and the app route
            answers with a sign-in wall instead of the argument. */}
        <Link to={`${PRESS_DATA_PATH}#grove`}>Make your own &#8594;</Link>
      </p>
    </figure>
  );
}

/**
 * A photograph inside the body, at the width of the text.
 *
 * Never wider. The rail is sticky and travels with the reader, so anything
 * that breaks out past the column collides with whatever is in the rail at
 * that moment. The lead picture is the one that gets the page.
 */
function BodyImage({ src, alt, caption, credit }) {
  return (
    <figure className="cp-ar__inline">
      <img src={src} alt={alt} loading="lazy" />
      <figcaption className="cp-ar__cap">
        {caption}
        {credit ? <span className="cp-ar__credit">{credit}</span> : null}
      </figcaption>
    </figure>
  );
}

/** Two pictures that are one comparison, side by side in the column. */
function BodyPair({ images }) {
  return (
    <div className="cp-ar__pair2">
      {images.map((image) => (
        <BodyImage key={image.src + image.alt} {...image} />
      ))}
    </div>
  );
}

/**
 * One collection the piece draws on, resolved against the reader.
 *
 * Open collections offer the file. Closed ones say what opens them and stop.
 * A reader who has just finished the article is the most receptive audience
 * the upgrade will ever have, and the least deserving of a trick.
 */
function DrawnFrom({ id, user }) {
  const entry = PRESS_CATALOG_BY_ID[id];
  if (!entry) return null;
  const open = canOpenDataset(user, entry);
  const upgrade = upgradeFor(entry);
  return (
    <li className={`cp-ar__draw${open ? "" : " is-locked"}`}>
      <span className="cp-ar__drawcap">{groupOf(entry.id)?.name ?? "Collection"}</span>
      <h3 className="cp-ar__drawname">{entry.name}</h3>
      <p className="cp-ar__drawblurb">{entry.blurb}</p>
      {open ? (
        // The file, right here. The per-collection pages are gone: a tile
        // is a download everywhere in the product, and this block keeps
        // that contract at the end of a piece.
        <button type="button" className="cp-ar__take" onClick={() => downloadCsv(entry)}>
          {/* Same honesty as the shelf tiles: what downloads is ten real rows
              of the collection's flagship table, not the collection, and a
              collection without even a sample delivers its description. The
              label says which one is arriving. */}
          {hasReleaseFile(entry)
            ? "Download a ten-row sample"
            : "Download the collection description"}{" "}
          <span aria-hidden="true">&#8595;</span>
        </button>
      ) : (
        <p className="cp-ar__locked">
          Included in <TierName name={upgrade.name} />.{" "}
          {/* A Grove upgrade goes to the Grove section on the reader, same
              reasoning as the figure attribution: the app route is a
              sign-in wall for exactly the reader seeing this prompt. */}
          <Link className="cp-m__more" to={upgrade.sameProduct ? PRESS_DATA_PATH : `${PRESS_DATA_PATH}#grove`}>
            See what it opens <span aria-hidden="true">&#8594;</span>
          </Link>
        </p>
      )}
    </li>
  );
}

export default function CedarPressArticle() {
  const { articleId } = useParams();
  const { user, loading, logout } = useAuth();
  // Sitewide arrival language: the head fades in; the prose stays put.
  const fadeRoot = useFadeIn();
  const article = BY_ID[articleId];
  useDocumentTitle(article?.title ?? "Article not found");
  useEffect(() => {
    if (article?.id) track(EVENT.articleOpened, { article: article.id, dataset: article.datasetId });
  }, [article?.id, article?.datasetId]);
  // A piece opens at its headline, wherever the click came from.
  useScrollToTop(articleId);

  // While /me is still resolving, render nothing rather than flashing the
  // gate at a subscriber who is about to be recognized; same guard as the
  // main /press route.
  if (loading) return null;

  // Same entitlement gate as /press: this route matches separately, so
  // without its own check a direct visit rendered the whole hosted
  // subscriber article to any session, signed-out included. The gate's
  // styling is scoped beneath .teim-rd like every other Press surface, so
  // the wrapper has to come with it or the direct route renders the sign-in
  // unstyled.
  if (!canReadCedarPress(user)) {
    return (
      <div className="teim-rd teim-rd--paper">
        <PressGate user={user} />
      </div>
    );
  }

  // An id that is not a hosted piece is a dead URL rather than a blank page.
  // Pieces that publish on Tribal Business News never get this route, so
  // landing here for one is the same mistake as landing here for nothing.
  if (!article || !article.hosted) {
    return (
      <div className="teim-rd teim-rd--paper">
        <main id="cp-main" className="cp cp-page">
          <PressMast section="articles" />
          <PressBack />
          <section className="cp-nh">
            <h1 className="cp-nh__title">That piece is not here.</h1>
            <p className="cp-nh__sub">
              It may publish on Tribal Business News, or the address may be wrong. The reader
              lists everything Cedar Press carries.
            </p>
          </section>
          <p>
            <Link className="cp-m__more" to={PRESS_PATH}>
              Back home <span aria-hidden="true">&#8594;</span>
            </Link>
          </p>
        </main>
      </div>
    );
  }

  const drawn = article.draws ?? [article.datasetId];
  // The second rail unit is earned by length. On a short piece the rail
  // runs past the last paragraph and the grid row stretches to match it,
  // which leaves a hole where the article should have ended.
  const longEnough = article.body.length >= 12;

  return (
    <div className="teim-rd teim-rd--paper">
      <main id="cp-main" className="cp cp-page" ref={fadeRoot}>
        <PressMast user={user} onSignOut={() => logout()} section="articles" />

        {/* Back goes to the briefs, not the hub: a piece belongs to the
            articles page, and the footer carries the rest of the map. */}
        <PressBack label="All Data Briefs" to={PRESS_ARTICLES_PATH} />

        <article className="cp-ar">
          <header className="cp-ar__head cp-fade">
            <p className="cp-hero__access">{article.tag}</p>
            <h1 className="cp-ar__title">{article.title}</h1>
            <p className="cp-ar__dek">{article.dek}</p>
            <p className="cp-ar__meta">
              {article.byline} · {article.date}
              {article.minutes ? ` · ${article.minutes} min read` : ""}
            </p>
            {/* Invented numbers never read as findings: a demonstration
                placeholder states what it is before the reader reaches a
                statistic. The notice leaves with the flag, when sourced
                research replaces the piece. */}
          </header>

          {/* The attribution goes under the picture, where a reader looks for
              it. `credit` lands with the real photograph; until then the
              caption carries the description on its own. */}
          <figure className="cp-ar__figure">
            <img className="cp-ar__art" src={article.image} alt={article.imageAlt} />
            <figcaption className="cp-ar__cap">
              {article.caption ?? article.imageAlt}
              {article.credit ? <span className="cp-ar__credit">{article.credit}</span> : null}
            </figcaption>
          </figure>

          <div className="cp-ar__grid">
            <div className="cp-ar__body">
              {article.body.map((block, index) => {
                if (block.kind === BLOCK.H2) {
                  return <h2 key={index} className="cp-ar__h2">{block.text}</h2>;
                }
                if (block.kind === BLOCK.PULL) {
                  return <p key={index} className="cp-ar__pull">{block.text}</p>;
                }
                if (block.kind === BLOCK.FIGURE) {
                  return <Figure key={index} block={block} />;
                }
                if (block.kind === BLOCK.IMAGE) {
                  return <BodyImage key={index} {...block} />;
                }
                if (block.kind === BLOCK.PAIR) {
                  return <BodyPair key={index} images={block.images} />;
                }
                return <p key={index}>{block.text}</p>;
              })}
            </div>

            {/* The rail. Sponsorship beside the text, and the standing
                reminder of what the piece was made from. */}
            <aside className="cp-ar__rail">
              <PressAd slot={AD_SLOT.ARTICLE_RAIL} />
              <div className="cp-ar__railbox">
                <span className="cp-ar__railcap">Behind this piece</span>
                <ul className="cp-ar__raillist">
                  {drawn.map((id) => (
                    <li key={id}>{PRESS_CATALOG_BY_ID[id]?.name ?? id}</li>
                  ))}
                </ul>
                <Link className="cp-m__more" to={PRESS_METHODS_PATH}>
                  How these are built <span aria-hidden="true">&#8594;</span>
                </Link>
              </div>
              {longEnough ? <PressAd slot={AD_SLOT.ARTICLE_RAIL_LOWER} /> : null}
              {longEnough ? <PressAd slot={AD_SLOT.ARTICLE_RAIL_END} /> : null}
            </aside>
          </div>
        </article>

        <PressAd slot={AD_SLOT.ARTICLE_END} />

        {/* The end of every hosted piece: the data it came from, resolved
            against what this reader can open. */}
        <section className="cp-ar__data" aria-label="The data behind this article">
          <div className="cp-head">
            <span className="cp-sec__band">See the underlying data</span>
            <span className="cp-kind cp-kind--data">Collections you download</span>
          </div>
          <ul className="cp-ar__draws">
            {drawn.map((id) => <DrawnFrom key={id} id={id} user={user} />)}
          </ul>
        </section>

        <p className="cp-ar__end">
          <Link className="cp-ar__back" to={PRESS_ARTICLES_PATH}>
            <span aria-hidden="true">&#8592;</span> Back home
          </Link>
        </p>

        <PressFoot />
        <PressCedarFab />
      </main>
    </div>
  );
}
