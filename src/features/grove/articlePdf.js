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

import { BLOCK, TBN_URL } from "./pressArticles.js";
import { CONTACT_EMAIL, EARLY_ACCESS_HREF, EARLY_ACCESS_LABEL } from "./appLink.js";

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
 * to ask for early access while enrollment is closed (the door's wording,
 * 2026-10-06; see appLink.js). The PDF goes along through the system share sheet
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
    "Cedar Press will be available exclusively through a Tribal Business News membership. " +
      `Enrollment is not open yet; request early access at ${CONTACT_EMAIL}.`,
  ].join("\n");
  return {
    subject,
    body,
    href: `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`,
  };
}

/** The shape the page crops the lead photograph to for the PDF's band. */
export const PDF_LEAD = Object.freeze({ w: 480, h: 540 });

/**
 * Build the PDF.
 *
 * An editorial layout rather than a printout (owner, 2026-09-27: "more
 * asymmetric ... it seems too utilitarian"). The first page opens on a navy
 * band with the title on the left and the photograph, smaller, bleeding off
 * the right edge. Under it the text runs in a column on the left while a rail
 * on the right carries the highlights, the collections and the way to
 * subscribe. Figures break out of the column to the full width, the quote is
 * set large between hairlines, and the last page closes on a navy panel with
 * two buttons: open the brief, and get Cedar Press+ through Tribal Business
 * News.
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
  const names = (article.authors ?? []).map((a) => a.name).join(", ") || article.byline;
  doc.setProperties({
    title: pdfText(article.title),
    subject: pdfText(article.dek),
    author: pdfText(names),
    creator: "Cedar Press",
  });

  const M = 48;
  const COL = 336; // the text column
  const RAILX = M + COL + 28;
  const RAILW = PAGE.w - M - RAILX;
  const FULL = PAGE.w - 2 * M;
  const BOTTOM = PAGE.h - 58;
  let y = 0;
  let railBottom = 0; // page 1 only: where the rail ends, so text can widen below it

  const fill = (rgb) => doc.setFillColor(...rgb);
  const ink = (rgb) => doc.setTextColor(...rgb);
  const font = (style, size) => {
    doc.setFont("helvetica", style);
    doc.setFontSize(size);
  };
  const pageNo = () => doc.getCurrentPageInfo().pageNumber;
  // The text column is narrow beside the rail on page 1 and full width after.
  const colWidth = () => (pageNo() === 1 && y < railBottom ? COL : FULL);

  const runningHead = () => {
    font("bold", 7.5);
    ink(DTEAL);
    doc.text("CEDAR PRESS  ·  RESEARCH BRIEF", M, 36, { charSpace: 1 });
    font("normal", 7.5);
    ink(MUTED);
    const short = pdfText(article.title);
    doc.text(short.length > 70 ? `${short.slice(0, 68)}…` : short, PAGE.w - M, 36, { align: "right" });
    doc.setDrawColor(...TEAL);
    doc.setLineWidth(0.6);
    doc.line(M, 44, PAGE.w - M, 44);
  };
  // A figure that will not fit where it falls waits for the top of the next
  // page while the text keeps flowing, the way a printed page floats it,
  // rather than leaving half a page blank.
  const deferred = [];
  let drawFigure = () => {};
  const newPage = () => {
    doc.addPage();
    runningHead();
    y = 64;
    while (deferred.length) drawFigure(deferred.shift());
  };
  const room = (h) => {
    if (y + h > BOTTOM) newPage();
  };
  const para = (text, { size = 10.5, style = "normal", color = INK, lead: leading = 1.5, x = M, width } = {}) => {
    font(style, size);
    ink(color);
    let words = pdfText(text);
    // Re-wrap whenever the available width changes (the rail ends mid-paragraph).
    while (words) {
      room(size * leading);
      // Set on every line: a page break draws the running head in its own face.
      font(style, size);
      ink(color);
      const w = width ?? colWidth();
      const [line] = doc.splitTextToSize(words, w);
      if (!line) break;
      doc.text(line, x, y + size);
      y += size * leading;
      words = words.slice(line.length).replace(/^\s+/, "");
    }
  };

  // ── Page 1: the band. Title on the left, the photograph bleeding right.
  const bandH = 300;
  const photoW = 214;
  fill(NAVY);
  doc.rect(0, 0, PAGE.w, bandH, "F");
  if (lead?.src) {
    doc.addImage(lead.src, "JPEG", PAGE.w - photoW, 0, photoW, bandH);
    fill(TEAL);
    doc.rect(PAGE.w - photoW, bandH - 4, photoW, 4, "F");
  }
  const textW = PAGE.w - photoW - M - 30;
  font("bold", 8);
  ink(TEAL);
  doc.text("CEDAR PRESS  ·  RESEARCH BRIEF", M, 58, { charSpace: 1.4 });
  // The title takes the largest size at which title, dek and byline all fit
  // the band.
  const dekLines = (() => {
    font("normal", 10.5);
    return doc.splitTextToSize(pdfText(article.dek), textW).slice(0, 4);
  })();
  let tSize = 25;
  let titleLines = [];
  for (const size of [25, 23, 21, 19, 17]) {
    tSize = size;
    font("bold", size);
    titleLines = doc.splitTextToSize(pdfText(article.title), textW);
    const needed = 76 + titleLines.length * size * 1.16 + 24 + dekLines.length * 15 + 22;
    if (needed <= bandH - 22) break;
  }
  let ty = 76;
  ink([255, 255, 255]);
  font("bold", tSize);
  for (const line of titleLines) {
    doc.text(line, M, ty + tSize);
    ty += tSize * 1.16;
  }
  fill(TEAL);
  doc.rect(M, ty + 10, 40, 3, "F");
  ty += 24;
  font("normal", 10.5);
  ink([200, 210, 225]);
  for (const line of dekLines) {
    doc.text(line, M, ty + 10.5);
    ty += 15;
  }
  font("bold", 8.5);
  ink([255, 255, 255]);
  doc.text(pdfText(`${names}  ·  ${article.date}`).toUpperCase(), M, Math.max(ty + 22, bandH - 30), { charSpace: 0.6 });

  // ── Page 1: the rail. Highlights, collections, and the way in.
  let ry = bandH + 30;
  font("bold", 7.5);
  ink(DTEAL);
  doc.text("ARTICLE HIGHLIGHTS", RAILX, ry, { charSpace: 1.2 });
  ry += 14;
  for (const h of article.highlights ?? []) {
    font("bold", 9.5);
    const hl = doc.splitTextToSize(pdfText(h), RAILW - 16);
    fill(TEAL);
    doc.rect(RAILX, ry + 4.5, 9, 1.6, "F");
    ink(NAVY);
    hl.forEach((line, i) => doc.text(line, RAILX + 16, ry + 9 + i * 12.5));
    ry += hl.length * 12.5 + 10;
  }
  if (collections.length) {
    ry += 6;
    doc.setDrawColor(...TEAL);
    doc.setLineWidth(0.5);
    doc.line(RAILX, ry, RAILX + RAILW, ry);
    ry += 16;
    font("bold", 7.5);
    ink(DTEAL);
    doc.text(collections.length > 1 ? "COLLECTIONS USED" : "COLLECTION USED", RAILX, ry, { charSpace: 1.2 });
    ry += 6;
    for (const c of collections) {
      font("bold", 9.5);
      ink(NAVY);
      const cl = doc.splitTextToSize(pdfText(c.name), RAILW);
      cl.forEach((line, i) => doc.textWithLink(line, RAILX, ry + 12 + i * 12, { url: c.href }));
      ry += cl.length * 12 + 6;
    }
  }
  // The subscribe card, navy, with its link on the whole card.
  ry += 12;
  font("normal", 9);
  const pitch = doc.splitTextToSize("Cedar Press+ will open every collection behind this brief, through a Tribal Business News membership. Enrollment is not open yet.", RAILW - 24);
  const cardH = 36 + pitch.length * 12.5 + 26;
  fill(NAVY);
  doc.roundedRect(RAILX, ry, RAILW, cardH, 6, 6, "F");
  font("bold", 11);
  ink([255, 255, 255]);
  doc.text("Read the data", RAILX + 12, ry + 22);
  font("normal", 9);
  ink([200, 210, 225]);
  pitch.forEach((line, i) => doc.text(line, RAILX + 12, ry + 38 + i * 12.5));
  font("bold", 9.5);
  ink([95, 217, 204]);
  doc.text(EARLY_ACCESS_LABEL, RAILX + 12, ry + cardH - 14);
  doc.link(RAILX, ry, RAILW, cardH, { url: EARLY_ACCESS_HREF });
  railBottom = ry + cardH + 8;

  // ── The text.
  y = bandH + 26;
  if (article.demonstration) {
    para("Illustrative figures: this brief's charts use example data while the research behind it is completed.", {
      size: 8.5,
      style: "italic",
      color: MUTED,
    });
    y += 4;
  }
  const imgHeight = (chart) => (chart?.src ? Math.min(300, Math.round((FULL * chart.h) / chart.w)) : 0);
  const notesHeight = (block) => {
    font("normal", 8);
    return (block.notes ?? []).reduce((n, note) => n + doc.splitTextToSize(pdfText(note), FULL - 40).length * 10.5, 0);
  };
  const figureHeight = ({ block, chart }) => 40 + imgHeight(chart) + notesHeight(block) + 16;

  const evidenceSourceLink = (source) => {
    const label = pdfText(source.title || source.publisher || "Source");
    font("normal", 8);
    const lines = doc.splitTextToSize(label, FULL).slice(0, 3);
    const height = Math.max(12, lines.length * 11);
    room(height + 6);
    font("normal", 8);
    ink(DTEAL);
    doc.text(lines, M, y + 8);
    doc.link(M, y, FULL, height, { url: source.url });
    y += height + 6;
  };
  const drawEvidence = (block, number) => {
    if (pageNo() === 1 && y < railBottom) y = railBottom;
    room(64);
    para("FIGURE " + number, { size: 8, style: "bold", color: DTEAL, width: FULL });
    para(block.caption, { size: 12, style: "bold", width: FULL });
    y += 6;
    const rows = block.chart === "relationships" ? block.relationships
      : block.chart === "timeline" ? block.events : block.rows;
    for (const row of rows) {
      const heading = block.chart === "relationships"
        ? row.from + " " + row.relationship + " " + row.to + " (as of " + row.asOf + ")"
        : block.chart === "timeline" ? row.date + ": " + row.title
        : row.entity + ": " + row.role + " (as of " + row.asOf + ")";
      room(42);
      para(heading, { size: 10, style: "bold", width: FULL });
      para(row.detail, { size: 9, width: FULL });
      y += 4;
      for (const source of row.sources) evidenceSourceLink(source);
      y += 5;
    }
    for (const note of block.notes) para(note, { size: 8, color: MUTED, width: FULL });
    para(block.source, { size: 8, style: "bold", color: MUTED, width: FULL });
    for (const source of block.sources) evidenceSourceLink(source);
    y += 12;
  };

  drawFigure = (fig) => {
    // Figures break out of the column to the full width.
    const { block, chart, n } = fig;
    if (y < railBottom && pageNo() === 1) y = railBottom;
    const imgH = imgHeight(chart);
    const boxH = figureHeight(fig);
    room(Math.min(boxH, BOTTOM - 70));
    fill(TINT);
    doc.roundedRect(M, y, FULL, boxH, 6, 6, "F");
    font("bold", 7.5);
    ink(DTEAL);
    doc.text(`FIGURE ${n}`, M + 14, y + 18, { charSpace: 1.2 });
    font("bold", 11);
    ink(NAVY);
    doc.text(pdfText(block.caption), M + 14, y + 33, { maxWidth: FULL - 28 });
    let fy = y + 42;
    if (chart?.src) {
      const w = Math.min(FULL - 28, Math.round((imgH * chart.w) / chart.h));
      doc.addImage(chart.src, "PNG", M + 14, fy, w, imgH);
      fy += imgH + 8;
    }
    font("normal", 8);
    ink(MUTED);
    for (const note of block.notes ?? []) {
      for (const line of doc.splitTextToSize(pdfText(note), FULL - 40)) {
        doc.text(line, M + 14, fy + 8);
        fy += 10.5;
      }
    }
    y += boxH + 18;
  };
  let figureAt = 0;
  for (const block of article.body ?? []) {
    if (block.kind === BLOCK.H2) {
      room(46);
      y += 10;
      fill(TEAL);
      doc.rect(M, y, 22, 2.5, "F");
      y += 9;
      para(block.text, { size: 14, style: "bold", color: NAVY, lead: 1.3 });
      y += 3;
    } else if (block.kind === BLOCK.PULL) {
      // Set large between hairlines: in the column beside the rail on page 1,
      // across the page after it, so it never leaves the column half empty.
      const shape = () => {
        const w = pageNo() === 1 && y < railBottom ? COL : FULL;
        font("bold", w === COL ? 14 : 16);
        const lead = w === COL ? 18.5 : 21;
        const lines = doc.splitTextToSize(pdfText(block.text), w - 30);
        return { qW: w, qLead: lead, q: lines, h: lines.length * lead + 30 };
      };
      let { qW, qLead, q, h } = shape();
      if (y + h + 10 > BOTTOM) {
        newPage();
        ({ qW, qLead, q, h } = shape());
      }
      doc.setDrawColor(...TEAL);
      doc.setLineWidth(0.8);
      doc.line(M, y + 4, M + qW, y + 4);
      font("bold", 34);
      ink(TEAL);
      doc.text("\u201c", M - 2, y + 38);
      font("bold", qW === COL ? 14 : 16);
      ink(NAVY);
      q.forEach((line, i) => doc.text(line, M + 30, y + 30 + i * qLead));
      y += h;
      doc.setDrawColor(...TEAL);
      doc.line(M, y, M + qW, y);
      y += 18;
    } else if (block.kind === BLOCK.FIGURE) {
      if (["relationships", "timeline", "evidenceTable"].includes(block.chart)) {
        figureAt += 1;
        drawEvidence(block, figureAt);
        continue;
      }
      const fig = { block, chart: figures[figureAt], n: figureAt + 1 };
      figureAt += 1;
      // A figure runs full width, so on page 1 it can only start below the
      // rail. Defer it when it will not fit there but the column still has a
      // real stretch of page for the text that follows.
      const top = pageNo() === 1 ? Math.max(y, railBottom) : y;
      if (figureHeight(fig) > BOTTOM - top && BOTTOM - y > 150) deferred.push(fig);
      else drawFigure(fig);
    } else if (block.kind === BLOCK.P) {
      para(block.text);
      y += 8;
    }
  }

  while (deferred.length) drawFigure(deferred.shift());

  // ── The close: a navy panel with two buttons.
  if (y < railBottom && pageNo() === 1) y = railBottom;
  const endH = 150;
  room(endH + 10);
  y += 8;
  fill(NAVY);
  doc.roundedRect(M, y, FULL, endH, 8, 8, "F");
  font("bold", 7.5);
  ink(TEAL);
  doc.text("KEEP READING", M + 22, y + 28, { charSpace: 1.4 });
  font("bold", 17);
  ink([255, 255, 255]);
  doc.text("The research, and the data behind it, on Cedar Press", M + 22, y + 52, { maxWidth: FULL - 44 });
  font("normal", 9.5);
  ink([200, 210, 225]);
  doc.text("Not a subscriber? Cedar Press will be available through a Tribal Business News membership. Enrollment is not open yet.", M + 22, y + 72, { maxWidth: FULL - 44 });
  const btn = (label, href, x, primary) => {
    font("bold", 10);
    const w = doc.getTextWidth(label) + 32;
    if (primary) {
      fill(DTEAL);
      doc.roundedRect(x, y + 96, w, 30, 6, 6, "F");
      ink([255, 255, 255]);
    } else {
      doc.setDrawColor(255, 255, 255);
      doc.setLineWidth(0.8);
      doc.roundedRect(x, y + 96, w, 30, 6, 6, "S");
      ink([255, 255, 255]);
    }
    doc.text(label, x + 16, y + 115);
    doc.link(x, y + 96, w, 30, { url: href });
    return w;
  };
  const w1 = btn(EARLY_ACCESS_LABEL, EARLY_ACCESS_HREF, M + 22, true);
  btn("Open this brief on Cedar Press", url, M + 22 + w1 + 12, false);
  y += endH;

  // ── Footer on every page.
  const pages = doc.getNumberOfPages();
  const host = (() => {
    try {
      return new URL(url).host;
    } catch {
      return "";
    }
  })();
  for (let i = 1; i <= pages; i += 1) {
    doc.setPage(i);
    doc.setDrawColor(222, 228, 232);
    doc.setLineWidth(0.5);
    doc.line(M, PAGE.h - 40, PAGE.w - M, PAGE.h - 40);
    font("normal", 7.5);
    ink(MUTED);
    doc.textWithLink("Cedar Press, from Lumecon and Tribal Business News", M, PAGE.h - 26, { url: TBN_URL });
    doc.textWithLink(`${host || "Cedar Press"}  ·  ${i} / ${pages}`, PAGE.w - M, PAGE.h - 26, { url, align: "right" });
  }

  return doc.output("blob");
}
