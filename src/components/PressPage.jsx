// Cedar Press: the signed-in page for the joint data brand.
//
// Ported from the app (teim-app, src/pages/CedarPress.jsx) when Cedar Press
// became a standalone site. Same deliberate shape: masthead, journalism,
// data, the citation register, one upsell band, footer — plus the upload
// panel, which is the standalone site's own addition. Router links into the
// app became links to lumecon.ai, and the app's auth became src/auth.js;
// everything else renders as it did inside the product.
import { useRef, useState } from "react";

import { FIGURES } from "./figures.jsx";
import UploadPanel from "./UploadPanel.jsx";
import {
  LAUNCH_COLLECTION,
  collectionCsv,
  figuresByDownloads,
} from "../data/collection.js";
import { LUMECON_URL, PRESS_ARTICLES, TBN_URL } from "../data/pressArticles.js";
import { CITATIONS, REPORT_CITATION_HREF, citationCountFor } from "../data/pressCitations.js";
import { storedUploads } from "../data/uploads.js";
import { currentTheme, setTheme } from "../theme.js";

function downloadCsv(dataset) {
  const csv = collectionCsv(dataset.id);
  if (!csv) return;
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${dataset.id}-${dataset.version}-demonstration.csv`;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

function ArticleCard({ article, compact = false }) {
  const dataset = LAUNCH_COLLECTION.find((item) => item.id === article.datasetId);
  return (
    <a
      className={compact ? "cp-art cp-art--compact" : "cp-art cp-art--lead"}
      href={article.href}
      target="_blank"
      rel="noreferrer"
    >
      {/* Sector photography stands in until the real brief publishes with
          its own image. The card links to Tribal Business News, where the
          briefs run. */}
      <div className="cp-art__art">
        <img className="cp-art__img" src={article.image} alt={article.imageAlt} loading="lazy" />
      </div>
      <div className="cp-art__body">
        <span className="cp-art__tag">{article.tag}</span>
        <h3 className="cp-art__title">{article.title}</h3>
        <p className="cp-art__dek">{article.dek}</p>
        <span className="cp-art__meta">
          {article.date} · from {dataset?.name} {dataset?.version}
        </span>
      </div>
    </a>
  );
}

// A row of cards that rotates once the shelf outgrows it. With three or
// fewer items the row simply fills; as the catalog grows past what fits,
// arrows appear and the row scrolls card by card. Wired now so adding a
// fourth dataset or a fourth brief changes nothing but the list.
function Strip({ items, renderItem, ariaLabel }) {
  const ref = useRef(null);
  const rotates = items.length > 3;
  const scrollByCard = (direction) => {
    const el = ref.current;
    if (!el) return;
    const card = el.firstElementChild;
    const step = card ? card.getBoundingClientRect().width + 18 : 360;
    el.scrollBy({ left: direction * step, behavior: "smooth" });
  };
  return (
    <div className="cp-stripwrap">
      {rotates ? (
        <button type="button" className="cp-strip__arrow" aria-label="Previous" onClick={() => scrollByCard(-1)}>
          ←
        </button>
      ) : null}
      <div className="cp-strip" ref={ref} aria-label={ariaLabel}>
        {items.map(renderItem)}
      </div>
      {rotates ? (
        <button type="button" className="cp-strip__arrow" aria-label="Next" onClick={() => scrollByCard(1)}>
          →
        </button>
      ) : null}
    </div>
  );
}

// Cedar's floating launcher, the same one the product renders. The chat
// needs the app's signed-in session, so on the standalone page the launcher
// opens an honest note; when Cedar grows a public press surface this
// becomes the real widget with no other change.
function CedarFab() {
  const [open, setOpen] = useState(false);
  return (
    <div className="cedar-widget cedar-widget--launcher-only">
      {open ? (
        <div className="cedar-widget__note" role="status">
          <p>
            Cedar answers questions about the collection inside Cedar Grove today. Asking
            from this page arrives with the pilot — until then,{" "}
            <a href="mailto:contact@lumecon.ai?subject=Cedar%20Press%20question">
              send us the question
            </a>{" "}
            and a person answers it.
          </p>
        </div>
      ) : null}
      <button
        type="button"
        className="cedar-widget__launcher"
        aria-label="Open Ask Cedar for Cedar Press"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        <span className="cedar-widget__status-dot" aria-hidden="true" />
        <span className="cedar-widget__launcher-copy">
          <span className="cedar-widget__launcher-label">Ask Cedar</span>
          <span className="cedar-widget__launcher-context">Cedar Press</span>
        </span>
      </button>
    </div>
  );
}

function DataCard({ figure }) {
  const dataset = LAUNCH_COLLECTION.find((item) => item.id === figure.id);
  const [showRows, setShowRows] = useState(false);
  const Figure = FIGURES[figure.kind];
  return (
    <div className="gvc-fig">
      <span className="gvc-fig__cap">
        {figure.title} · {figure.basis}
      </span>
      {Figure ? <Figure points={figure.points} /> : null}
      <div className="gvc-fig__acts">
        <button type="button" className="gv-btn gv-btn--primary" onClick={() => downloadCsv(dataset)}>
          Download the data
        </button>
        <button
          type="button"
          className="gv-btn gv-btn--primary"
          aria-expanded={showRows}
          onClick={() => setShowRows((open) => !open)}
        >
          {showRows ? "Hide the data" : "View the data"}
        </button>
      </div>
      {showRows ? (
        <p className="cp-rows">
          {figure.points.map((point) => `${point.label}: ${point.value}`).join(" · ")}
        </p>
      ) : null}
      <p className="cp-figmeta">
        {dataset.downloads.toLocaleString("en-US")} downloads · {dataset.rowsLabel} · vintage {dataset.vintage} · {dataset.version} · updated {dataset.updated}
      </p>
    </div>
  );
}

export default function PressPage({ user, onSignOut }) {
  const [uploads, setUploads] = useState(storedUploads);
  const [theme, setThemeState] = useState(currentTheme);
  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    setThemeState(next);
  };

  return (
    <div className="cp">
      <header className="cp-mast">
        <span className="cp-mast__word">CEDAR PRESS</span>
        <span className="cp-mast__of">
          A <a href={TBN_URL} target="_blank" rel="noreferrer">Tribal Business News</a> ×{" "}
          <a href={LUMECON_URL} target="_blank" rel="noreferrer">Lumecon</a> partnership
        </span>
        <span className="cp-mast__user">
          {user.email}
          <button
            type="button"
            className="cp-mast__chromebtn"
            onClick={toggleTheme}
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          >
            {theme === "dark" ? "Light" : "Dark"}
          </button>
          <button type="button" className="cp-mast__chromebtn" onClick={onSignOut}>
            Sign out
          </button>
        </span>
      </header>

      <section className="cp-hero">
        <p className="cp-hero__access">
          Available through a Tribal Business News subscription · included with Cedar Grove
        </p>
        <h1>Making Indian Country&rsquo;s economy impossible to overlook.</h1>
        <p>
          Cedar Press joins original economic datasets, rigorous journalism, transparent
          method and working software into one continuously improving public resource for
          Indian Country. It is built by the team that created foundational Native economic
          datasets at the Federal Reserve&rsquo;s Center for Indian Country Development,
          including the federal contracting data its research uses. The records begin in
          public sources, the datasets are original research products shaped by inclusion
          rules and entity resolution, and every figure here carries its method with the
          rows one click away.
        </p>
      </section>

      <section className="cp-sec" aria-label="Latest from the data">
        <span className="cp-sec__band">Latest from the data</span>
        {/* A front page, not a row of tiles: the newest brief leads at
            double width, the rest stack beside it, and growth appends to
            the stack with the archive living at TBN. */}
        <div className="cp-artgrid">
          <ArticleCard article={PRESS_ARTICLES[0]} />
          <div className="cp-artstack">
            {PRESS_ARTICLES.slice(1).map((article) => (
              <ArticleCard key={article.id} article={article} compact />
            ))}
            <a className="cp-artmore" href={TBN_URL} target="_blank" rel="noreferrer">
              All Data Briefs publish at Tribal Business News →
            </a>
          </div>
        </div>
      </section>

      <section className="cp-sec" id="data" aria-label="The collection">
        <span className="cp-sec__band">The collection · most downloaded first</span>
        <Strip
          ariaLabel="The collection"
          items={figuresByDownloads()}
          renderItem={(figure) => <DataCard key={figure.id} figure={figure} />}
        />
      </section>

      <UploadPanel uploads={uploads} onChange={() => setUploads(storedUploads())} />

      <section className="cp-sec cp-citeband" aria-label="The citation register">
        <div>
          <span className="cp-sec__band">Cited in the wild</span>
          <h2 className="cp-cedar__title">Where the data shows up.</h2>
          <p className="cp-cite__lede">
            Every known public use of a Cedar Press dataset is recorded here: who cited it,
            which release they used, and where the piece appeared. The register is part of
            the method, because data cited in public earns trust in public and a correction
            can reach everyone who relied on the release it touches.
          </p>
          <p className="cp-cite__lede">
            We watch for uses ourselves and take reports from readers, and the count begins
            with the pilot&rsquo;s first public release.
          </p>
        </div>
        <div className="cp-citecard">
          <span className="cp-citecard__cap">The register</span>
          {LAUNCH_COLLECTION.map((dataset) => (
            <div key={dataset.id} className="cp-citecard__row">
              <span>{dataset.name}</span>
              <b>{CITATIONS.length ? citationCountFor(dataset.id) : "—"}</b>
            </div>
          ))}
          {CITATIONS.length ? (
            <ul className="cp-cite__list">
              {CITATIONS.map((entry) => (
                <li key={entry.id}>
                  <a href={entry.href} target="_blank" rel="noreferrer">
                    {entry.outlet} · {entry.piece}
                  </a>
                  <span className="cp-cite__meta">
                    {entry.date} · {entry.datasetId} {entry.version}
                  </span>
                </li>
              ))}
            </ul>
          ) : null}
          <a className="gv-btn gv-btn--primary cp-citecard__cta" href={REPORT_CITATION_HREF}>
            Cited the data? Tell us
          </a>
        </div>
      </section>

      <section className="cp-more" aria-label="More from the data">
        {/* Cedar goes unmentioned here on purpose: its launcher is on this
            page, so the card sells what the page cannot show. */}
        <div className="cp-more__card">
          <h3>Go deeper with Cedar Grove</h3>
          <p>
            Cedar Grove is a continuously maintained knowledge base for Indian Country. It
            holds the full collection with complete histories, bulk export and benchmarks,
            plus the public data your reporting, compliance and analysis routinely need:
            Census, BLS, BEA and more. New economic development datasets land as subscriber
            requests and newsroom needs shape the roadmap, and Grove learns your
            organization&rsquo;s workflows the longer you use it. One price covers unlimited
            users in one organization.
          </p>
          <a className="gv-btn gv-btn--primary" href={LUMECON_URL} target="_blank" rel="noreferrer">
            Explore Cedar Grove
          </a>
        </div>
        <div className="cp-more__card">
          <h3>Measure your economic impact</h3>
          <p>
            The Lumecon platform runs full economic impact analysis. It turns budgets,
            payroll and program records into defensible estimates of jobs, income and
            output, with the same data discipline behind every number. Every estimate
            ships with its assumptions and sources stated, ready for council packets,
            lenders and federal review.
          </p>
          <div className="cp-more__acts">
            <a className="gv-btn gv-btn--primary" href={LUMECON_URL} target="_blank" rel="noreferrer">
              Explore the platform
            </a>
            <a
              className="gv-btn gv-btn--quiet"
              href="https://lumecon.ai/methodology"
              target="_blank"
              rel="noreferrer"
            >
              Read the methodology
            </a>
          </div>
        </div>
      </section>

      <CedarFab />

      <section className="cp-sec cp-feedback" aria-label="Feedback">
        <div>
          <span className="cp-sec__band">Make it better</span>
          <p className="cp-feedback__text">
            Tell us what the data should do next, what a page gets wrong, or what you could
            not find. Feedback goes to the team that builds the datasets, and it shapes what
            the partnership builds next.
          </p>
        </div>
        <a className="gv-btn gv-btn--primary" href="mailto:contact@lumecon.ai?subject=Cedar%20Press%20feedback">
          Send feedback
        </a>
      </section>

      <footer className="cp-foot">
        <span>
          Cedar Press · corrections and method notes ·{" "}
          <a href="mailto:contact@lumecon.ai?subject=Cedar%20Press%20feedback">send feedback</a>
        </span>
        <span>
          <a href={TBN_URL} target="_blank" rel="noreferrer">tribalbusinessnews.com</a>
          {" · "}
          <a href={LUMECON_URL} target="_blank" rel="noreferrer">lumecon.ai</a>
        </span>
        <span>Demonstration data · the launch collection ships with the pilot</span>
      </footer>
    </div>
  );
}
