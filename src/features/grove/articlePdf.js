// REVIEW OWNER: Havala
//
// A research brief as a PDF, to pass around (owner, 2026-09-27): "share
// article ... it'll generate a PDF and you can email it to someone ... pretty
// much just like the article, the figures, maybe a note about subscribing to
// Cedar Press+ through Tribal Business News, easy to use hyperlinks."
//
// The piece as it reads on the page: the title band, the lead picture in its
// duotone, the highlights, the text, the quote, every figure with its notes
// and source, and at the end the links a recipient needs: the brief itself,
// the collections it used, and how to get Cedar Press+.
//
// jsPDF is imported only when somebody asks for the file, so a reader who
// never shares pays nothing for it. The page prepares the pictures (the
// figures rasterized from the SVG on screen, the lead photograph toned);
// this module only lays out pages, which keeps it testable in node.

import { BLOCK, TBN_PLANS_URL, TBN_URL } from "./pressArticles.js";

const PAGE = { w: 612, h: 792, m: 54 };
const NAVY = [9, 19, 43];
const TEAL = [15, 181, 165];
const DTEAL = [10, 127, 116];
const TINT = [242, 250, 248];
const INK = [26, 32, 44];
const MUTED = [100, 114, 121];

/**
 * The standard fonts carry Windows-1252 only. Anything outside it would print
 * as a wrong glyph, so it is spelled out or dropped, never left to chance.
 */
// The Windows-1252 characters above Latin-1 that the standard fonts carry.
const CP1252_EXTRA = new Set([
  0x2013, 0x2014, 0x2018, 0x2019, 0x201c, 0x201d, 0x2022, 0x2026, 0x20ac, 0x2122,
  0x0152, 0x0153, 0x0160, 0x0161, 0x0178, 0x017d, 0x017e, 0x0192, 0x02c6, 0x02dc,
  0x2020, 0x2021, 0x2030, 0x2039, 0x203a,
]);
const SPELLED = new Map([
  [0x2212, "-"], // minus sign
  [0x00a0, " "], // no-break space
]);

export function pdfText(text) {
  let out = "";
  for (const ch of String(text ?? "")) {
    const code = ch.codePointAt(0);
    if (SPELLED.has(code)) out += SPELLED.get(code);
    else if ((code >= 0x20 && code <= 0xff) || code === 0x0a || CP1252_EXTRA.has(code)) out += ch;
  }
  return out.replace(/\s+$/g, "").replace(/^\s+/g, "");
}

/** The file a brief downloads as: its title, lowercased and hyphenated. */
export function pdfFileName(article) {
  const slug = String(article?.title ?? "cedar-press-brief")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
  return `${slug || "cedar-press-brief"}.pdf`;
}

/**
 * The email a sharer starts from. A mailto link cannot carry an attachment,
 * so the body stands on its own: what the piece is, where to read it, and how
 * to get Cedar Press+. The PDF goes along through the system share sheet
 * where the browser has one, and is downloaded to attach by hand where not.
 */
export function shareEmail(article, url) {
  const subject = `Cedar Press: ${article.title}`;
  const body = [
    "I thought you would find this Cedar Press research brief useful.",
    "",
    article.title,
    article.dek,
    "",
    `Read it on Cedar Press: ${url}`,
    "",
    `Cedar Press+ is available through a Tribal Business News membership: ${TBN_PLANS_URL}`,
  ].join("\n");
  return {
    subject,
    body,
    href: `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`,
  };
}

/**
 * Build the PDF.
 *
 * @param {object} input
 * @param {object} input.article   the PRESS_ARTICLES entry
 * @param {string} input.url       the brief's absolute address
 * @param {Array<{name: string, href: string}>} input.collections
 * @param {{src: string, w: number, h: number} | null} input.lead
 *        the toned lead photograph as a JPEG data URL, or null
 * @param {Array<{src: string, w: number, h: number} | null>} input.figures
 *        each figure's chart as a PNG data URL, in body order
 * @param {object} [input.jsPDF]   the constructor, for tests; imported if absent
 * @returns {Promise<Blob>}
 */
export async function buildArticlePdf({ article, url, collections = [], lead = null, figures = [], jsPDF }) {
  const Ctor = jsPDF ?? (await import("jspdf")).jsPDF;
  const doc = new Ctor({ unit: "pt", format: "letter", compress: true });
  doc.setProperties({
    title: pdfText(article.title),
    subject: pdfText(article.dek),
    author: pdfText((article.authors ?? []).map((a) => a.name).join(", ") || article.byline),
    creator: "Cedar Press",
  });

  const W = PAGE.w - 2 * PAGE.m;
  let y = 0;

  const fill = (rgb) => doc.setFillColor(...rgb);
  const ink = (rgb) => doc.setTextColor(...rgb);
  const font = (style, size) => {
    doc.setFont("helvetica", style);
    doc.setFontSize(size);
  };
  const newPage = () => {
    doc.addPage();
    y = PAGE.m;
  };
  const room = (h) => {
    if (y + h > PAGE.h - PAGE.m - 18) newPage();
  };
  // Wrapped text, broken across pages a line at a time.
  const lines = (text, { size = 10.5, style = "normal", color = INK, lead: leading = 1.45, width = W, x = PAGE.m } = {}) => {
    font(style, size);
    ink(color);
    for (const line of doc.splitTextToSize(pdfText(text), width)) {
      room(size * leading);
      doc.text(line, x, y + size);
      y += size * leading;
    }
  };
  const link = (label, href, { size = 10.5, x = PAGE.m } = {}) => {
    font("bold", size);
    ink(DTEAL);
    room(size * 1.6);
    doc.textWithLink(pdfText(label), x, y + size, { url: href });
    y += size * 1.6;
  };

  // The band: publication, title, dek, authors and date, on navy.
  font("bold", 22);
  const titleLines = doc.splitTextToSize(pdfText(article.title), W);
  font("normal", 11);
  const dekLines = doc.splitTextToSize(pdfText(article.dek), W);
  const bandH = 58 + titleLines.length * 26 + 10 + dekLines.length * 15 + 34;
  fill(NAVY);
  doc.rect(0, 0, PAGE.w, bandH, "F");
  font("bold", 8);
  ink(TEAL);
  doc.text("CEDAR PRESS  ·  RESEARCH BRIEF", PAGE.m, 40, { charSpace: 1.2 });
  font("bold", 22);
  ink([255, 255, 255]);
  y = 50;
  for (const line of titleLines) {
    doc.text(line, PAGE.m, y + 22);
    y += 26;
  }
  fill(TEAL);
  doc.rect(PAGE.m, y + 6, 48, 3, "F");
  y += 16;
  font("normal", 11);
  ink([205, 214, 228]);
  for (const line of dekLines) {
    doc.text(line, PAGE.m, y + 11);
    y += 15;
  }
  const names = (article.authors ?? []).map((a) => a.name).join(", ") || article.byline;
  font("bold", 9);
  ink([255, 255, 255]);
  doc.text(pdfText(`By ${names}  ·  ${article.date}`), PAGE.m, y + 20);
  y = bandH + 18;

  if (lead?.src) {
    const h = Math.round((W * lead.h) / lead.w);
    doc.addImage(lead.src, "JPEG", PAGE.m, y, W, h);
    y += h + 6;
    if (article.caption) lines(article.caption, { size: 8.5, color: MUTED, lead: 1.35 });
    y += 8;
  }

  if (article.highlights?.length) {
    font("normal", 10.5);
    const wrapped = article.highlights.map((h) => doc.splitTextToSize(pdfText(h), W - 44));
    const boxH = 38 + wrapped.reduce((n, l) => n + l.length * 14.5 + 6, 0);
    room(boxH);
    fill(TINT);
    doc.setDrawColor(...TEAL);
    doc.setLineWidth(0.6);
    doc.roundedRect(PAGE.m, y, W, boxH, 6, 6, "FD");
    font("bold", 11);
    ink(NAVY);
    doc.text("Article highlights", PAGE.m + 16, y + 24);
    let hy = y + 40;
    font("normal", 10.5);
    ink(INK);
    for (const l of wrapped) {
      fill(DTEAL);
      doc.circle(PAGE.m + 20, hy + 3.5, 2, "F");
      for (const line of l) {
        doc.text(line, PAGE.m + 30, hy + 7);
        hy += 14.5;
      }
      hy += 6;
    }
    y += boxH + 18;
  }

  if (article.demonstration) {
    lines("Illustrative figures: this brief's charts use example data while the research behind it is completed.", {
      size: 8.5,
      style: "italic",
      color: MUTED,
    });
    y += 6;
  }

  let figureAt = 0;
  for (const block of article.body ?? []) {
    if (block.kind === BLOCK.H2) {
      room(40);
      y += 8;
      fill(TEAL);
      doc.rect(PAGE.m, y, 24, 2.5, "F");
      y += 8;
      lines(block.text, { size: 13.5, style: "bold", color: NAVY, lead: 1.3 });
      y += 4;
    } else if (block.kind === BLOCK.PULL) {
      font("bold", 13);
      const q = doc.splitTextToSize(pdfText(block.text), W - 56);
      const boxH = q.length * 18 + 30;
      room(boxH + 12);
      fill(NAVY);
      doc.roundedRect(PAGE.m, y, W, boxH, 6, 6, "F");
      font("bold", 30);
      ink(TEAL);
      doc.text("“", PAGE.m + 14, y + 34);
      font("bold", 13);
      ink([255, 255, 255]);
      q.forEach((line, i) => doc.text(line, PAGE.m + 42, y + 26 + i * 18));
      y += boxH + 16;
    } else if (block.kind === BLOCK.FIGURE) {
      const chart = figures[figureAt];
      figureAt += 1;
      const imgH = chart?.src ? Math.round((W * chart.h) / chart.w) : 0;
      room(Math.min(imgH, 360) + 60);
      y += 6;
      lines(block.caption, { size: 10.5, style: "bold", color: NAVY, lead: 1.35 });
      if (chart?.src) {
        const h = Math.min(imgH, 360);
        const w = Math.round((h * chart.w) / chart.h);
        doc.addImage(chart.src, "PNG", PAGE.m, y + 4, w, h);
        y += h + 10;
      }
      for (const note of block.notes ?? []) lines(`•  ${note}`, { size: 8.5, color: MUTED, lead: 1.35 });
      y += 10;
    } else if (block.kind === BLOCK.P) {
      lines(block.text);
      y += 7;
    }
  }

  // The way in, at the end: the brief, its collections, and Cedar Press+.
  // Measured first, so the box is drawn to fit what goes in it.
  const inner = W - 32;
  font("bold", 12);
  const headH = doc.splitTextToSize("Read the full brief, and the data behind it, on Cedar Press", inner).length * 12 * 1.45;
  font("normal", 10);
  const pitch = "Not a subscriber? Cedar Press+ is available through a Tribal Business News membership.";
  const pitchH = doc.splitTextToSize(pitch, inner).length * 10 * 1.45;
  const endH = 16 + headH + 10.5 * 1.6 + (collections.length ? 9 * 1.45 + collections.length * 10 * 1.6 : 0) + 6 + pitchH + 10.5 * 1.6 + 12;
  room(endH + 10);
  y += 10;
  fill(TINT);
  doc.setDrawColor(...TEAL);
  doc.roundedRect(PAGE.m, y, W, endH, 6, 6, "FD");
  const top = y;
  y += 16;
  lines("Read the full brief, and the data behind it, on Cedar Press", { size: 12, style: "bold", color: NAVY, x: PAGE.m + 16, width: inner });
  link("Open this brief on Cedar Press", url, { x: PAGE.m + 16 });
  if (collections.length) {
    lines("Collections used", { size: 9, style: "bold", color: MUTED, x: PAGE.m + 16 });
    for (const c of collections) link(c.name, c.href, { size: 10, x: PAGE.m + 16 });
  }
  y += 6;
  lines(pitch, { size: 10, color: INK, x: PAGE.m + 16, width: inner });
  link("Get Cedar Press+ through Tribal Business News", TBN_PLANS_URL, { x: PAGE.m + 16 });
  y = Math.max(y, top + endH);

  // A footer on every page, with the brief's address.
  const pages = doc.getNumberOfPages();
  for (let i = 1; i <= pages; i += 1) {
    doc.setPage(i);
    font("normal", 8);
    ink(MUTED);
    doc.textWithLink("Cedar Press, from Lumecon and Tribal Business News", PAGE.m, PAGE.h - 28, { url: TBN_URL });
    doc.text(`Page ${i} of ${pages}`, PAGE.w - PAGE.m, PAGE.h - 28, { align: "right" });
  }

  return doc.output("blob");
}
