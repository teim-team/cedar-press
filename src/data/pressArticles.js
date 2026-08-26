/**
 * PURPOSE
 * The article slots on the Cedar Press page: journalism built from the
 * collection, one card per published piece.
 *
 * The page renders whatever this list holds, newest first. Publishing a new
 * Data Brief means appending an entry here (and later, when articles live in
 * a CMS, this module becomes the fetch that reads them). Each article names
 * the dataset it draws from, so an article can never advertise data the page
 * does not show.
 *
 * PROTOTYPE LIMITATIONS
 * These three are demonstration placeholders, one per launch dataset, written
 * to be replaced by the real first Data Briefs. `href` points at Tribal
 * Business News, where the briefs publish; each entry gets its article's real
 * URL on publication, and `image` its real photograph. Until then the cards
 * run sector photography in the house duotones.
 */

export const TBN_URL = "https://tribalbusinessnews.com";
export const LUMECON_URL = "https://lumecon.ai";

export const PRESS_ARTICLES = Object.freeze([
  Object.freeze({
    id: "brief-deals",
    href: TBN_URL,
    image: "/lanes/professional-wide.webp",
    imageAlt: "A negotiation around a conference table",
    datasetId: "deals",
    tag: "Data Brief",
    title: "Announced deals in Indian Country are running ahead of any year in the series",
    dek: "Energy and project finance lead 2026's announced transactions, the Deals database shows, with closings confirmed against primary sources before they enter totals.",
    date: "July 2026",
  }),
  Object.freeze({
    id: "brief-contractors",
    href: TBN_URL,
    image: "/lanes/construction-wide.webp",
    imageAlt: "Crews working a large construction site",
    datasetId: "contractors",
    tag: "Data Brief",
    title: "Federal contracting to Native entities rises for a fourth straight quarter",
    dek: "Award histories rolled up to parent tribes, ANCs and NHOs show broad growth, led by 8(a) participants.",
    date: "June 2026",
  }),
  Object.freeze({
    id: "brief-funding",
    href: TBN_URL,
    image: "/lanes/publicadmin-wide.webp",
    imageAlt: "The United States Capitol",
    datasetId: "funding",
    tag: "Data Brief",
    title: "Where federal dollars reached Indian Country in FY2025",
    dek: "Assistance awards by program and recipient, from the Funding dataset's first full-year release.",
    date: "May 2026",
  }),
]);
