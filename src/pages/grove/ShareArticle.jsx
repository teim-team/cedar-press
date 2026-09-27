import { useState } from "react";

import { applyDuotone } from "../../features/grove/duotone.js";
import { buildArticlePdf, pdfFileName, shareEmail } from "../../features/grove/articlePdf.js";
import { EVENT, track } from "../../features/grove/telemetry.js";

/**
 * SHARE THE BRIEF (owner, 2026-09-27): a PDF of the piece, figures and all,
 * that a reader can email to somebody, so the research travels and brings
 * people back. Three plain actions, beside the title where a reader looks:
 * email it, download the PDF, copy the link.
 *
 * "Email it" hands the PDF to the system share sheet where the browser has
 * one (phones, Safari, Edge), which is the only way a web page can put a
 * file into an email. Everywhere else it downloads the PDF and opens a
 * drafted email with the link, and says to attach the file, because a
 * mailto link cannot carry one.
 */

const STYLE_PROPS = [
  "fill",
  "fill-opacity",
  "stroke",
  "stroke-width",
  "stroke-dasharray",
  "stroke-opacity",
  "opacity",
  "font-family",
  "font-size",
  "font-weight",
  "letter-spacing",
  "text-anchor",
  "dominant-baseline",
];

/** A figure's on-screen SVG as a PNG, with its computed styles inlined so
 * the stylesheet's custom properties survive leaving the page. */
async function rasterize(svg) {
  const box = svg.viewBox?.baseVal;
  const w = box?.width || svg.clientWidth || 460;
  const h = box?.height || svg.clientHeight || 190;
  const clone = svg.cloneNode(true);
  const from = [svg, ...svg.querySelectorAll("*")];
  const to = [clone, ...clone.querySelectorAll("*")];
  from.forEach((node, i) => {
    const computed = getComputedStyle(node);
    const style = STYLE_PROPS.map((p) => `${p}:${computed.getPropertyValue(p)}`).join(";");
    to[i].setAttribute("style", style);
  });
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  clone.setAttribute("width", String(w));
  clone.setAttribute("height", String(h));
  // A data URL, not a blob: the page's CSP allows img-src 'self' data: only.
  const url = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(new XMLSerializer().serializeToString(clone))}`;
  {
    const img = await loadImage(url);
    const scale = 3;
    const canvas = document.createElement("canvas");
    canvas.width = w * scale;
    canvas.height = h * scale;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    return { src: canvas.toDataURL("image/png"), w, h };
  }
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("image failed to load"));
    img.src = src;
  });
}

/** The lead photograph cropped to the band's proportion and toned with the
 * piece's wash, as it reads on the page. */
async function tonedLead(src, tone) {
  const img = await loadImage(src);
  const w = 1200;
  const h = Math.round((w * 7) / 16);
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  const ratio = Math.max(w / img.naturalWidth, h / img.naturalHeight);
  const dw = img.naturalWidth * ratio;
  const dh = img.naturalHeight * ratio;
  ctx.drawImage(img, (w - dw) / 2, (h - dh) / 2, dw, dh);
  const pixels = ctx.getImageData(0, 0, w, h);
  applyDuotone(pixels.data, tone);
  ctx.putImageData(pixels, 0, 0);
  return { src: canvas.toDataURL("image/jpeg", 0.86), w, h };
}

function saveBlob(blob, name) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

export function ShareArticle({ article, path, collections }) {
  const [busy, setBusy] = useState(null);
  const [said, setSaid] = useState("");

  // Absolute addresses, built when a reader acts: the page is prerendered,
  // and the PDF and the email are read somewhere else entirely.
  const abs = (to) => new URL(to, window.location.origin).href;
  const url = typeof window === "undefined" ? path : abs(path);

  const makePdf = async () => {
    const svgs = [...document.querySelectorAll(".cp-ar__body .cp-ar__fig")].map((fig) => fig.querySelector("svg.pf"));
    const figures = [];
    for (const svg of svgs) figures.push(svg ? await rasterize(svg).catch(() => null) : null);
    const lead = article.image ? await tonedLead(article.image, article.tone).catch(() => null) : null;
    const blob = await buildArticlePdf({
      article,
      url,
      collections: collections.map((c) => ({ name: c.name, href: abs(c.path) })),
      lead,
      figures,
    });
    return { blob, name: pdfFileName(article) };
  };

  const run = async (kind, action) => {
    if (busy) return;
    setBusy(kind);
    setSaid("");
    try {
      await action();
      track(EVENT.articleShared, { article: article.id, via: kind });
    } catch (error) {
      if (error?.name !== "AbortError") setSaid("That did not work. Try again, or copy the link instead.");
    } finally {
      setBusy(null);
    }
  };

  const download = () =>
    run("pdf", async () => {
      const { blob, name } = await makePdf();
      saveBlob(blob, name);
      setSaid("The PDF is downloading.");
    });

  const email = () =>
    run("email", async () => {
      const { blob, name } = await makePdf();
      const mail = shareEmail(article, url);
      const file = new File([blob], name, { type: "application/pdf" });
      if (navigator.canShare?.({ files: [file] })) {
        await navigator.share({ files: [file], title: mail.subject, text: mail.body });
        return;
      }
      saveBlob(blob, name);
      window.location.href = mail.href;
      setSaid("The PDF downloaded. Attach it to the email that just opened.");
    });

  const copy = () =>
    run("link", async () => {
      await navigator.clipboard.writeText(url);
      setSaid("Link copied.");
    });

  return (
    <div className="cp-share" role="group" aria-label="Share this brief">
      <button type="button" className="cp-share__btn cp-share__btn--main" onClick={email} disabled={Boolean(busy)}>
        {busy === "email" ? "Preparing the PDF…" : "Email this brief"}
      </button>
      <button type="button" className="cp-share__btn" onClick={download} disabled={Boolean(busy)}>
        {busy === "pdf" ? "Preparing…" : "Download PDF"}
      </button>
      <button type="button" className="cp-share__btn" onClick={copy} disabled={Boolean(busy)}>
        Copy link
      </button>
      <span className="cp-share__said" aria-live="polite">{said}</span>
    </div>
  );
}
