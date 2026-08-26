/**
 * REVIEW OWNER: Havala
 *
 * PURPOSE
 * The article slots on the Cedar Press page: journalism built from the
 * collection, one card per published piece.
 *
 * The page renders whatever this list holds, newest first, in a horizontal
 * strip. Publishing new original research means appending an entry here (and later,
 * when articles live in a CMS, this module becomes the fetch that reads them).
 * Each article names the collection it draws from, and the card's artwork is that
 * collection's figure, so an article can never advertise data the page does not
 * show.
 *
 * TWO PLACES A PIECE CAN LIVE
 * Some research publishes on Tribal Business News, where it does the work of
 * bringing people to the product. Some is hosted here, where a subscriber
 * reads it beside the data it came from. `hosted` decides which: a hosted
 * piece carries `body` and opens on Cedar Press, and everything else opens on
 * TBN through `href`.
 *
 * Hosting is what makes the page sellable. A hosted article has a rail for
 * sponsorship, an audience you can count and a subject a buyer can choose:
 * federal contracting is a different advertiser from gaming. It also lets the
 * piece do two jobs the TBN version cannot. `draws` names the collections
 * behind it, so a reader can take the data if their tier opens it and is
 * shown what opens it if not, which is the most honest upgrade prompt in the
 * product. And a figure carries where it was made, because every chart in
 * these pieces is built in Cedar Grove and saying so is the strongest case
 * Grove has.
 *
 * PROTOTYPE LIMITATIONS
 * There are three stock photographs in the repository and the demonstration
 * pieces reuse them, so the same picture appears in more than one place. That
 * is a stand-in for photography, not a layout decision; every image slot gets
 * its own picture and its own credit on publication.
 *
 * These three are demonstration placeholders, one per launch collection,
 * written to be replaced by the first real briefs. Headlines follow the same
 * claim discipline as the collection findings: descriptive statements the
 * named dataset actually supports. Bodies are written to exercise the layout
 * and the entitlement paths rather than to be published. `image` gets a real
 * photograph on publication; until then the cards run the sector photography
 * the pitch already carries, in the house duotones.
 *
 * `demonstration: true` is what keeps that honest on the page. Every number
 * in these bodies and figures is invented, so every surface that renders a
 * demonstration piece has to say so where the reader is looking: the card
 * carries a demonstration tag and the article page carries a notice above
 * the body. The flag comes off an entry only when sourced research replaces
 * the placeholder, at which point the surfaces render it as research again.
 */

/**
 * The blocks a hosted body is made of.
 *
 * A piece runs two or three photographs, not one. The lead runs the width of
 * the page and the rest run the width of the text, which is the hierarchy a
 * reader already knows from print: the opening picture is the piece, the ones
 * inside it are evidence. `pair` sets two side by side in the column, for the
 * case where two pictures are one comparison.
 *
 * Nothing renders a chart. A decorative figure is the fake dashboard this
 * product is trying not to be, so `figure` is a caption, a source and where it
 * was built.
 *
 * In-body pictures never break out past the text column. The rail is sticky
 * and travels with the reader, so anything wider than the column collides with
 * whatever is in the rail at that moment.
 */
export const BLOCK = Object.freeze({
  P: "p",
  H2: "h2",
  PULL: "pull",
  FIGURE: "figure",
  IMAGE: "image",
  PAIR: "pair",
});

import { CHART } from "./pressCharts.js";

export const TBN_URL = "https://tribalbusinessnews.com";
export const LUMECON_URL = "https://lumecon.ai";

export const PRESS_ARTICLES = Object.freeze([
  Object.freeze({
    id: "brief-deals",
    hosted: true,
    image: "/pitch/lanes/professional-wide.webp",
    imageAlt: "A negotiation around a conference table",
    caption:
      "Announced capital in energy and project finance is concentrated in a small number of large transactions, which makes the annual figure sensitive to a single closing.",
    datasetId: "deals",
    draws: Object.freeze(["deals", "funding"]),
    tag: "Original Research",
    demonstration: true,
    title: "Announced deals in Indian Country are running ahead of any year in the series",
    dek: "Energy and project finance lead 2026's announced transactions, the Deals database shows, with closings confirmed against primary sources before they enter totals.",
    date: "July 2026",
    byline: "Cedar Press research desk",
    minutes: 4,
    body: Object.freeze([
      Object.freeze({
        kind: BLOCK.P,
        text:
          "Announced transactions in Indian Country are running ahead of any comparable period in the series, and the composition has moved as much as the count. Energy and project finance carry most of the increase, with tribal governments and tribal enterprises appearing as principals rather than as counterparties. That is a change in kind as much as in volume: a nation financing its own generation capacity is a different economic actor from one leasing land to somebody else's project.",
      }),
      Object.freeze({
        kind: BLOCK.P,
        text:
          "The distinction matters for anyone reading a total. Announced and closed are labeled separately in the Deals collection, and a transaction enters totals only once its status is confirmed against a primary source. A year that looks strong on announcements can settle differently, and the gap between the two lines is itself worth watching. In 2023 roughly a fifth of announced capital had not closed twelve months later, most of it in a single sector.",
      }),
      Object.freeze({
        kind: BLOCK.FIGURE,
        chart: CHART.LINE,
        caption: "Announced against confirmed transactions, by quarter",
        source: "deals",
        series: Object.freeze(["announced", "confirmed"]),
        points: Object.freeze([
          Object.freeze({ label: "Q2'25", announced: 31, confirmed: 24 }),
          Object.freeze({ label: "Q3'25", announced: 38, confirmed: 29 }),
          Object.freeze({ label: "Q4'25", announced: 34, confirmed: 28 }),
          Object.freeze({ label: "Q1'26", announced: 47, confirmed: 33 }),
          Object.freeze({ label: "Q2'26", announced: 52, confirmed: 35 }),
        ]),
        notes: Object.freeze([
          "Announced counts a transaction at first public report. Confirmed counts it once its status is verified against a primary source, which is usually one to three quarters later.",
          "The most recent quarter is therefore always understated on the confirmed line.",
          "Undisclosed values are counted as transactions and excluded from any dollar total.",
        ]),
      }),
      Object.freeze({ kind: BLOCK.H2, text: "Who is on the other side" }),
      Object.freeze({
        kind: BLOCK.P,
        text:
          "Resolving counterparties is where a transaction record becomes readable. A financing that names a subsidiary tells you very little until the subsidiary is joined to its parent nation or corporation, and the same acquisition can appear three times under three names across a decade of filings. Announcements name the entity as it was styled that week, which is rarely the entity a researcher is looking for.",
      }),
      Object.freeze({
        kind: BLOCK.P,
        text:
          "The work is unglamorous and it is most of the value. A tribal enterprise formed in 1998, renamed in 2006, reorganized under a holding company in 2014 and acquired in 2021 leaves four record trails that no public source connects. Cedar maintains those relationships over time, which is why an ownership change recorded here also corrects rows in Contracting and Gaming. Corrections travel to every release they touch, and a figure cited last quarter stays reproducible.",
      }),
      Object.freeze({
        kind: BLOCK.PULL,
        text: "The records are public. Knowing that four names over twelve years are one enterprise is the work.",
      }),
      Object.freeze({
        kind: BLOCK.P,
        text:
          "The practical effect shows up in concentration. Read at face value, the transaction record looks more distributed than it is, because one buyer appears as several. Resolved to parents, the top ten acquirers account for a meaningfully larger share of announced capital than the unresolved list suggests, and the direction of that error is consistent across every year in the series.",
      }),
      Object.freeze({
        kind: BLOCK.PAIR,
        images: Object.freeze([
          Object.freeze({
            src: "/pitch/lanes/publicadmin-wide.webp",
            alt: "The United States Capitol",
            caption: "Federal programs remain the counterparty on a large share of project financings.",
          }),
          Object.freeze({
            src: "/pitch/lanes/construction-wide.webp",
            alt: "Crews working a large construction site",
            caption: "Construction starts trail announcements by two to four quarters in most of the series.",
          }),
        ]),
      }),
      Object.freeze({ kind: BLOCK.H2, text: "What to watch" }),
      Object.freeze({
        kind: BLOCK.P,
        text:
          "Project finance in energy is the line to follow into next year. Announced capital is concentrated in a small number of large projects, so a single delay moves the annual figure more than the underlying rate of activity would suggest. Two of the largest announcements in the current period are at the permitting stage, where timelines are least predictable, and either one slipping would take the year below the prior period on announced capital while activity itself was flat.",
      }),
      Object.freeze({
        kind: BLOCK.P,
        text:
          "Property and hospitality are the quieter half of the increase and the steadier one. Transactions there are smaller, more numerous and less exposed to a single closing, which makes them a better read on whether the underlying rate of activity has moved. They are also where tribal enterprises most often appear as buyers of operating businesses rather than as developers, which is a different capability and a different balance sheet.",
      }),
      Object.freeze({
        kind: BLOCK.P,
        text:
          "Bond issuance is the third thread and the one most sensitive to conditions outside Indian Country. Issuance held up through the rate environment of the last two years, which was not the expectation, and the reasons are worth a separate piece. The collection carries issuance alongside the acquisitions and financings so the three can be read against each other rather than separately.",
      }),
      Object.freeze({ kind: BLOCK.H2, text: "How to read the totals" }),
      Object.freeze({
        kind: BLOCK.P,
        text:
          "Inclusion rules travel with every release, so a transaction missing from the collection is a documented gap rather than a silent one. Where a deal is reported but unconfirmed it sits as announced and is visible as such, which is the difference between a figure that can be cited and one that cannot. Where a value is not disclosed, the transaction is counted and the value is not, rather than being estimated into the total.",
      }),
      Object.freeze({
        kind: BLOCK.P,
        text:
          "Anyone reproducing the numbers here should note the as-of date beside each figure. The collections update continuously, every correction is logged on the What\u2019s New page, and a change that moves a total says so there. A figure cited with its date stays explainable: the log shows what has moved since and why.",
      }),
      Object.freeze({
        kind: BLOCK.P,
        text:
          "One caution on comparison. Transaction counts across Indian Country cannot be read against a national deal index without adjusting for what each includes, and most published indices exclude the tribal enterprise structures that account for a large share of the activity here. The comparison people usually want is between periods within this series, which is why the reconstructed history matters more for this collection than a benchmark against somebody else's.",
      }),
    ]),
  }),
  Object.freeze({
    id: "brief-contractors",
    hosted: true,
    image: "/pitch/lanes/construction-wide.webp",
    imageAlt: "Crews working a large construction site",
    caption:
      "Construction carries most of the obligation volume and almost none of the recent increase, which is in professional and technical services.",
    datasetId: "contractors",
    draws: Object.freeze(["contractors", "subcontracting"]),
    tag: "Original Research",
    demonstration: true,
    title: "Federal contracting to Native entities rises for a fourth straight quarter",
    dek: "Award histories rolled up to parent tribes, ANCs and NHOs show broad growth, led by 8(a) participants.",
    date: "June 2026",
    byline: "Cedar Press research desk",
    minutes: 4,
    body: Object.freeze([
      Object.freeze({
        kind: BLOCK.P,
        text:
          "Obligations to Native-owned firms rose for a fourth consecutive quarter, and the growth is broader than the headline suggests. Rolled up to parent tribes, ANCs and NHOs, the increase reaches more entities than in any quarter of the prior year rather than concentrating in the largest holders. The number of distinct parents winning at least one award is the highest in the series.",
      }),
      Object.freeze({
        kind: BLOCK.P,
        text:
          "8(a) participants lead, which is the expected result and also the one most often misread. Participation is a status with a start and an end, so a firm that held it in 2019 and does not hold it now should not be counted as an 8(a) award today. Reading the program as a permanent attribute of a company overstates its current share and understates how many firms have graduated out of it and kept winning work.",
      }),
      Object.freeze({
        kind: BLOCK.FIGURE,
        chart: CHART.STACKED,
        caption: "Obligations by parent entity type, by quarter",
        source: "contractors",
        series: Object.freeze(["Tribal enterprise", "ANC subsidiary", "NHO subsidiary"]),
        points: Object.freeze([
          Object.freeze({ label: "Q3'25", "Tribal enterprise": 41, "ANC subsidiary": 33, "NHO subsidiary": 9 }),
          Object.freeze({ label: "Q4'25", "Tribal enterprise": 44, "ANC subsidiary": 34, "NHO subsidiary": 10 }),
          Object.freeze({ label: "Q1'26", "Tribal enterprise": 49, "ANC subsidiary": 35, "NHO subsidiary": 11 }),
          Object.freeze({ label: "Q2'26", "Tribal enterprise": 56, "ANC subsidiary": 36, "NHO subsidiary": 13 }),
        ]),
        notes: Object.freeze([
          "These are obligations rather than receipts. An obligation is the government committing funds; the work and the payment can fall in later periods.",
          "Each award is attributed to the parent the firm had at the date of award rather than the parent it has now.",
          "Band order is fixed across every quarter, so only the bottom band and the total share a baseline.",
        ]),
      }),
      Object.freeze({
        kind: BLOCK.P,
        text:
          "Resolving the vendor list to parents is what turns a procurement record into an industry picture. Federal reporting names the awardee, and the awardee is frequently a subsidiary two or three levels below the nation or corporation that owns it. A single ANC can appear under a dozen names across agencies, none of which reference each other, and none of which are wrong.",
      }),
      Object.freeze({ kind: BLOCK.H2, text: "The subaward layer" }),
      Object.freeze({
        kind: BLOCK.P,
        text:
          "Prime awards are the visible half. Matching subaward activity to the same resolved entities shows work moving between Native firms that neither record describes on its own, and it is where the growth in the smaller tiers actually appears. A prime award to one tribal enterprise that subcontracts to three others is four firms working, and the prime record shows one.",
      }),
      Object.freeze({
        kind: BLOCK.P,
        text:
          "The pattern is not uniform. In construction, subaward activity to other Native firms is a small share of the prime value. In professional and technical services it is substantially higher, which is consistent with how those contracts are staffed and is worth knowing before drawing conclusions about the depth of the sector from prime awards alone.",
      }),
      Object.freeze({
        kind: BLOCK.PULL,
        text: "The industry only appears once the vendors are joined to who owns them.",
      }),
      Object.freeze({
        kind: BLOCK.P,
        text:
          "Both collections are maintained against the same entity layer, so a parent renaming or a subsidiary being acquired reaches every historical award at once rather than leaving two records that disagree. That is also why a correction filed in the Deals collection can move a figure here: the entity is the same entity, and the relationship is maintained in one place.",
      }),
      Object.freeze({
        kind: BLOCK.IMAGE,
        src: "/pitch/lanes/professional-wide.webp",
        alt: "A meeting around a conference table",
        caption:
          "Professional and technical services carry the quarters that moved, on smaller awards spread across more firms.",
      }),
      Object.freeze({ kind: BLOCK.H2, text: "Where the growth is not" }),
      Object.freeze({
        kind: BLOCK.P,
        text:
          "Construction and facilities services carry most of the volume and almost none of the increase. The quarters that moved are professional services and information technology, where the average award is smaller and the number of distinct entities winning work is higher. Read only in dollars, the sector looks flat; read in entities and awards, it does not.",
      }),
      Object.freeze({
        kind: BLOCK.P,
        text:
          "That composition is worth watching for a reason beyond the totals. A base of many small awards across many firms is a different kind of exposure from a base of few large ones, and it responds differently when an agency changes how it buys. Consolidation of small contracts into larger vehicles has been the direction of federal procurement for a decade, and the firms most exposed to it are the ones the headline number is least sensitive to.",
      }),
      Object.freeze({
        kind: BLOCK.FIGURE,
        chart: CHART.SANKEY,
        caption: "Prime obligations reaching subcontracted work, by sector",
        source: "subcontracting",
        flows: Object.freeze([
          Object.freeze({ from: "Construction", to: "Native subcontractors", value: 12 }),
          Object.freeze({ from: "Construction", to: "Other subcontractors", value: 46 }),
          Object.freeze({ from: "Professional services", to: "Native subcontractors", value: 27 }),
          Object.freeze({ from: "Professional services", to: "Other subcontractors", value: 19 }),
          Object.freeze({ from: "Information technology", to: "Native subcontractors", value: 16 }),
          Object.freeze({ from: "Information technology", to: "Other subcontractors", value: 14 }),
        ]),
        notes: Object.freeze([
          "Ribbon width is the only quantity. Vertical position carries no meaning.",
          "Covers reported subawards only. Work performed in-house by the prime does not appear.",
          "A subcontractor is counted as Native where ownership is established from filings or primary-source confirmation.",
        ]),
      }),
      Object.freeze({ kind: BLOCK.H2, text: "What the collection does and does not claim" }),
      Object.freeze({
        kind: BLOCK.P,
        text:
          "The collection publishes obligations as reported, with the entity resolution applied on top and documented. Where a firm's parent changed during the period covered, the award is attributed to the parent it had at the time of award rather than the one it has now. Both attributions are defensible and they answer different questions; the one used here is stated with the release so a figure can be reproduced or deliberately recomputed the other way.",
      }),
      Object.freeze({
        kind: BLOCK.P,
        text:
          "Obligations are not receipts. An obligation is the government committing funds, and the timing of the work and the payment can sit in later periods or, on a terminated contract, never arrive. For questions about revenue rather than about award activity, the obligation series is the wrong instrument, and the methodology note says so rather than leaving a reader to find out from a discrepancy.",
      }),
      Object.freeze({
        kind: BLOCK.P,
        text:
          "Nor does the collection assert that every Native-owned firm appears. Ownership is established from filings, registrations and primary-source confirmation, and a firm that is Native-owned but has never had to declare it in a record Cedar reads will be missing. That gap is documented with the release, it is smaller at the top of the award distribution than at the bottom, and it is the honest limit on any statement about the total size of the sector rather than about the awards themselves.",
      }),
    ]),
  }),
  Object.freeze({
    id: "brief-funding",
    // Published on Tribal Business News rather than here: the mix is the
    // point, and a piece that runs on TBN is the one doing the work of
    // bringing somebody to the product in the first place.
    href: TBN_URL,
    image: "/pitch/lanes/publicadmin-wide.webp",
    imageAlt: "The United States Capitol",
    datasetId: "funding",
    tag: "Original Research",
    demonstration: true,
    title: "Where federal dollars reached Indian Country in FY2025",
    dek: "Assistance awards by program and recipient, from the Funding collection's first full-year release.",
    date: "May 2026",
  }),
]);
