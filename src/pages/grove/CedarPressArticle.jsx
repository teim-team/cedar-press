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
// can buy a subject: federal contracting and natural resources are different buyers, and
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

import { Fragment, useEffect, useState } from "react";
import { Link, useParams } from "react-router";


import { useAuth } from "../../context/useAuth";
import { useFadeIn } from "../../features/grove/useFadeIn";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { EVENT, track } from "../../features/grove/telemetry.js";
import { PressBack, PressFoot, PressMast } from "./PressChrome";
import { PRESS_FIGURES } from "../../components/grove/pressFigures";
import { AD_SLOT } from "../../features/grove/pressAds";
import {
  ARTICLE_IMAGE,
  BLOCK,
  LUMECON_URL,
  PRESS_ARTICLES,
  TBN_PLANS_URL,
  TBN_URL,
} from "../../features/grove/pressArticles";
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
import { GROVE_MARKETING_URL } from "../../features/grove/appLink.js";
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
function Figure({ block, lead = false }) {
  const entry = PRESS_CATALOG_BY_ID[block.source];
  const release = releaseFor(block.source);
  const Chart = PRESS_FIGURES[block.chart];
  return (
    <figure className={`cp-ar__fig${lead ? " cp-ar__fig--lead" : ""}`}>
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
        {/* To the Cedar Grove page on lumecon.ai, not /app/grove: a Press
            reader clicking this has no Grove entitlement, and the app route
            answers with a sign-in wall instead of the argument. */}
        <a href={GROVE_MARKETING_URL} target="_blank" rel="noreferrer">Make your own &#8594;</a>
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
      {/* Sized so the column does not reflow when the picture lands: the
          text below a body image is what a reader is in the middle of. */}
      <img
        src={src}
        alt={alt}
        width={ARTICLE_IMAGE.width}
        height={ARTICLE_IMAGE.height}
        loading="lazy"
      />
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
  // What the service said when it refused the file, connected; the same
  // feedback the shelf gives, so the button never appears to do nothing
  // (Codex, PR #68).
  const [refusal, setRefusal] = useState(null);
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
        <>
        <button
          type="button"
          className="cp-ar__take"
          onClick={() => {
            setRefusal(null);
            downloadCsv(entry).catch((error) => setRefusal(error?.message || "The download did not go through."));
          }}
        >
          {/* Same honesty as the shelf tiles: what downloads is ten real rows
              of the collection's flagship table, not the collection, and a
              collection without even a sample delivers its description. The
              label says which one is arriving. */}
          {hasReleaseFile(entry)
            ? "Download a ten-row sample"
            : "Download the collection description"}{" "}
          <span aria-hidden="true">&#8595;</span>
        </button>
        {refusal ? <p className="cp-ar__drawblurb" role="alert">{refusal}</p> : null}
        {/* THE WAY BACK IN, NOT JUST THE WAY OUT.
            This block offered a file and nothing else, so a reader who
            finished the piece and wanted to look at the records had to go to
            Collections and find the collection again — in a product where
            the collection page now opens on whichever one the link names.
            The table is the better of the two for most readers: the file is
            ten rows, this is the release in the viewer. */}
        <Link className="cp-ar__open" to={`${PRESS_DATA_PATH}?c=${entry.id}`}>
          Open it in the table <span aria-hidden="true">&#8594;</span>
        </Link>
        </>
      ) : (
        <p className="cp-ar__locked">
          Included in <TierName name={upgrade.name} />.{" "}
          {/* A Grove upgrade goes to the Cedar Grove page on lumecon.ai, same
              reasoning as the figure attribution: the app route is a
              sign-in wall for exactly the reader seeing this prompt. */}
          {upgrade.sameProduct ? (
            <Link className="cp-m__more" to={PRESS_DATA_PATH}>
              See what it opens <span aria-hidden="true">&#8594;</span>
            </Link>
          ) : (
            <a className="cp-m__more" href={GROVE_MARKETING_URL} target="_blank" rel="noreferrer">
              See what it opens <span aria-hidden="true">&#8594;</span>
            </a>
          )}
        </p>
      )}
    </li>
  );
}

/**
 * One collection the piece is built from, at the head of the page.
 *
 * Owner, 2026-09-27: the collection a brief used belongs up top, beside the
 * title, so a reader who has it can dive straight in and one who does not
 * sees what opens it. Open collections go to the viewer on that collection;
 * a closed one says which plan includes it and links to where that plan is
 * bought (a Tribal Business News membership for Cedar Press+, the Cedar
 * Grove page for Grove).
 */
function UsedCollection({ id, user }) {
  const entry = PRESS_CATALOG_BY_ID[id];
  if (!entry) return null;
  const open = canOpenDataset(user, entry);
  const upgrade = upgradeFor(entry);
  return (
    <li className={`cp-ar__use${open ? "" : " is-locked"}`}>
      <span className="cp-ar__usename">{entry.name}</span>
      {open ? (
        <Link className="cp-ar__usego" to={`${PRESS_DATA_PATH}?c=${entry.id}`}>
          Open the data <span aria-hidden="true">&#8594;</span>
        </Link>
      ) : (
        <a
          className="cp-ar__usego"
          href={upgrade.sameProduct ? TBN_PLANS_URL : GROVE_MARKETING_URL}
          target="_blank"
          rel="noreferrer"
        >
          Included in {upgrade.name}. Get access <span aria-hidden="true">&#8594;</span>
        </a>
      )}
    </li>
  );
}

export default function CedarPressArticle() {
  const { articleId } = useParams();
  const { user, loading } = useAuth();
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
  // Figures stay where the argument put them (owner, 2026-09-27). The first
  // one used to be lifted out to lead the page at full width, where its type
  // scaled to headline size and the piece opened on a chart instead of on
  // what it is and who wrote it.
  const body = article.body;
  // Authors with a face and a role; a piece that names only a byline still
  // gets a row, with initials where the photograph would be.
  const authors = article.authors?.length ? article.authors : [{ name: article.byline }];
  // An example sponsor unit sits in the text before the second section
  // heading, where a reader has settled into the piece (owner, 2026-09-27:
  // "it needs ad space examples").
  const headings = body.flatMap((b, i) => (b.kind === BLOCK.H2 ? [i] : []));
  const inlineAdAt = headings[1] ?? -1;

  return (
    <div className="teim-rd teim-rd--paper">
      <main id="cp-main" className="cp cp-page" ref={fadeRoot}>
        <PressMast section="articles" />

        {/* Back goes to the briefs, not the hub: a piece belongs to the
            articles page, and the footer carries the rest of the map. */}
        <PressBack label="All Data Briefs" to={PRESS_ARTICLES_PATH} />

        <article className="cp-ar">
          {/* THE HEAD OF THE PAGE, IN THE SHAPE THE CENTER FOR INDIAN COUNTRY
              DEVELOPMENT'S RESEARCH USES (owner, 2026-09-27): a navy band with
              the title, the dek, the date and the authors, each with a face
              and a role; then the lead picture, with three headlines from the
              piece in a box over its right side; then the collections the
              piece used, open to a reader who has them and priced for one who
              does not. */}
          <header className="cp-ar__hero cp-fade">
            <p className="cp-ar__tag">{article.tag}</p>
            <h1 className="cp-ar__title">{article.title}</h1>
            <span className="cp-ar__rule" aria-hidden="true" />
            <p className="cp-ar__dek">{article.dek}</p>
            <p className="cp-ar__meta">
              <span>{article.date}</span>
              {article.minutes ? <span>{article.minutes} min read</span> : null}
            </p>
            <section className="cp-ar__authors" aria-label="Authors">
              <h2 className="cp-ar__authorscap">{authors.length > 1 ? "Authors" : "Author"}</h2>
              <ul className="cp-ar__authorlist">
                {authors.map((author) => (
                  <li className="cp-ar__author" key={author.name}>
                    {author.photo ? (
                      <img className="cp-ar__face" src={author.photo} alt="" width="72" height="72" loading="lazy" />
                    ) : (
                      <span className="cp-ar__face cp-ar__face--mark" aria-hidden="true">
                        {author.name.split(/\s+/).filter((w) => /^[A-Z]/.test(w)).slice(0, 2).map((w) => w[0]).join("")}
                      </span>
                    )}
                    <span className="cp-ar__authorid">
                      <span className="cp-ar__by">{author.name}</span>
                      {author.role ? <span className="cp-ar__role">{author.role}</span> : null}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          </header>

          <div className="cp-ar__lead cp-fade">
            <figure className="cp-ar__figure cp-ar__heroimg">
              <img
                className="cp-ar__art"
                src={article.image}
                alt={article.imageAlt}
                width={ARTICLE_IMAGE.width}
                height={ARTICLE_IMAGE.height}
                fetchPriority="high"
              />
              <figcaption className="cp-ar__cap">
                {article.caption ?? article.imageAlt}
                {article.credit ? <span className="cp-ar__credit">{article.credit}</span> : null}
              </figcaption>
            </figure>
            {article.highlights?.length ? (
              <aside className="cp-ar__highlights" aria-label="Article highlights">
                <h2 className="cp-ar__hlcap">Article highlights</h2>
                <ul className="cp-ar__hllist">
                  {article.highlights.map((line) => <li key={line}>{line}</li>)}
                </ul>
              </aside>
            ) : null}
          </div>

          <div className="cp-ar__uses">
            <span className="cp-ar__usecap">
              {drawn.length > 1 ? "Collections used" : "Collection used"}
            </span>
            <ul className="cp-ar__uselist">
              {drawn.map((id) => <UsedCollection key={id} id={id} user={user} />)}
            </ul>
          </div>

          <div className="cp-ar__grid">
            <div className="cp-ar__body">
              {body.map((block, index) => {
                if (block.kind === BLOCK.H2) {
                  return (
                    <Fragment key={index}>
                      {index === inlineAdAt ? <PressAd slot={AD_SLOT.ARTICLE_INLINE} example /> : null}
                      <h2 className="cp-ar__h2">{block.text}</h2>
                    </Fragment>
                  );
                }
                if (block.kind === BLOCK.PULL) {
                  // The quote box: the line from the piece a reader should
                  // leave with, set apart rather than italicised in place.
                  return (
                    <blockquote key={index} className="cp-ar__quote">
                      <p className="cp-ar__pull">{block.text}</p>
                    </blockquote>
                  );
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
                {/* Named AND reachable. This rail listed the collections as
                    plain text beside a reader who was, by definition,
                    interested in them; the collection page opens on whichever
                    one a link names, so there is no reason to make somebody
                    go and find it. A collection their plan cannot open still
                    resolves — the page says what opens it, in place. */}
                <ul className="cp-ar__raillist">
                  {drawn.map((id) => (
                    <li key={id}>
                      <Link to={`${PRESS_DATA_PATH}?c=${id}`}>
                        {PRESS_CATALOG_BY_ID[id]?.name ?? id}
                      </Link>
                    </li>
                  ))}
                </ul>
                <Link className="cp-m__more" to={PRESS_METHODS_PATH}>
                  How these are built <span aria-hidden="true">&#8594;</span>
                </Link>
              </div>
              {longEnough ? <PressAd slot={AD_SLOT.ARTICLE_RAIL_LOWER} example /> : null}
              {longEnough ? <PressAd slot={AD_SLOT.ARTICLE_RAIL_END} example /> : null}
            </aside>
          </div>
        </article>

        <PressAd slot={AD_SLOT.ARTICLE_END} example />

        {/* The end of every hosted piece: the data it came from, resolved
            against what this reader can open. */}
        <section className="cp-ar__data cp-fade" aria-label="The data behind this article">
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
