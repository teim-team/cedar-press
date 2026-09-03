/**
 * REVIEW OWNER: Havala
 *
 * PURPOSE
 * The marks a Cedar Press figure may use, and the rules for choosing one.
 *
 * WHY THIS IS NOT collectionFigures.jsx
 * Cedar Grove draws three marks and draws them the same way every time. That
 * is correct for Grove: those figures are generated from a live workspace,
 * they have to be interactive, and a fixed vocabulary is what keeps a hundred
 * generated charts legible as a set. An editor building one figure for one
 * article is under no such constraint, and holding a published piece to
 * Grove's three marks would mean answering a distribution question with a bar
 * chart because a bar chart is what was available.
 *
 * So press figures have the wider vocabulary and Grove keeps the narrow one.
 * The trade is deliberate and runs the other way too: a press figure answers
 * a hover with its number and stops there, while a Grove figure is something
 * you can pull apart, refilter and requestion. The article says where its
 * figure was built and links to Grove, which is the whole marketing case.
 *
 * THE RULE IS THE QUESTION, NOT THE DATA
 * Pick the mark from what the sentence beside it is claiming. A shape chosen
 * because the numbers happen to fit it is how a figure ends up answering a
 * question nobody asked.
 *
 * WHAT IS NOT HERE, ON PURPOSE
 * No pie or donut. Angle is the hardest encoding to read and a part-to-whole
 * claim is better served by a stacked bar, which is in this list.
 * No dual axes. Two series on two scales can be made to show any relationship
 * an author wants, which is the definition of a chart that cannot be trusted.
 * No 3D, no gradients inside marks, no decorative axes.
 */

/** The marks. Each maps to one renderer in components/grove/pressFigures. */
export const CHART = Object.freeze({
  BARS: "bars",
  LINE: "line",
  HISTOGRAM: "histogram",
  STACKED: "stacked",
  TILEMAP: "tilemap",
  SANKEY: "sankey",
});

/**
 * Which mark answers which question, for an editor choosing one.
 *
 * `use` is the question. `avoid` is the case where it looks right and is not,
 * which is the more useful half: most bad figures are a reasonable mark
 * applied to the wrong claim.
 */
export const CHART_RULES = Object.freeze([
  Object.freeze({
    kind: CHART.BARS,
    name: "Bars",
    use: "Comparing a value across a handful of named things, or across periods you want read as discrete.",
    avoid: "A continuous series. Bars imply each column is its own case, and a monthly series is not.",
    axis: "Always from zero. A truncated bar axis exaggerates a difference by whatever fraction was cut.",
  }),
  Object.freeze({
    kind: CHART.LINE,
    name: "Line",
    use: "Change over time, and comparison between two or three series on the same scale.",
    avoid: "Categories with no order. A line between unrelated categories asserts a trend that does not exist.",
    axis: "May start above zero when the question is about movement, and the axis must say so.",
  }),
  Object.freeze({
    kind: CHART.HISTOGRAM,
    name: "Histogram",
    use: "The shape of a distribution: award sizes, transaction values, how concentrated something is.",
    avoid: "Comparing groups. Two histograms side by side are read as one, and rarely correctly.",
    axis: "Bin width is a choice that changes the shape, so the note says what it is.",
  }),
  Object.freeze({
    kind: CHART.STACKED,
    name: "Stacked bar",
    use: "Composition: how a total divides, and how that division moves between periods.",
    avoid: "Comparing the middle bands. Only the bottom band and the total have a common baseline.",
    axis: "From zero, and the band order is fixed across every bar or the eye reads noise as change.",
  }),
  Object.freeze({
    kind: CHART.TILEMAP,
    name: "State tile map",
    use: "Geography where every state should be equally visible, which is most questions about Indian Country.",
    avoid: "Anything below the state, and any question where physical area is the point.",
    axis: "One tile per state, equal size. A land-area map gives Alaska forty times the weight of Oklahoma.",
  }),
  Object.freeze({
    kind: CHART.SANKEY,
    name: "Flow",
    use: "Where money or work moves between two sets of things: agency to recipient, prime to subcontractor.",
    avoid: "More than about eight nodes a side, after which nobody can follow a ribbon.",
    axis: "Ribbon width is the only quantity. Vertical position carries no meaning and the note says so.",
  }),
]);

const RULE_BY_KIND = Object.freeze(
  Object.fromEntries(CHART_RULES.map((rule) => [rule.kind, rule])),
);

/** The rule for a mark, or null for a kind nobody has defined. */
export function chartRule(kind) {
  return RULE_BY_KIND[kind] ?? null;
}

/**
 * What every figure has to carry underneath it, whatever the mark.
 *
 * A chart is a claim, and a claim without its assumptions is an assertion.
 * These are the assumptions a reader needs to argue with the figure rather
 * than take it on faith, which is the only kind of figure worth publishing.
 */
export const FIGURE_REQUIREMENTS = Object.freeze([
  "The collection and release it was drawn from, so the number can be reproduced.",
  "What is counted and what is excluded, where either would surprise a reader.",
  "Any choice that changes the shape: a bin width, a truncated axis, an inflation basis, a cut-off date.",
  "Where the figure was built, which is Cedar Grove, and a route to build one.",
]);

/**
 * Whether a figure is publishable.
 *
 * A mark nobody has defined, or a figure with no notes, is a figure that has
 * not been finished. Used by the test rather than at render time: the page
 * should not be deciding at runtime whether an editor did their job.
 */
export function figureProblems(figure) {
  const problems = [];
  if (!chartRule(figure.kind)) problems.push(`unknown mark: ${figure.kind}`);
  if (!figure.caption) problems.push("no caption");
  if (!figure.source) problems.push("no source collection");

  // FIGURE_REQUIREMENTS asks for what is counted, what is excluded and any
  // shape-changing choice: that is at least two real notes, and a note has to
  // say something. A whitespace string satisfies neither.
  const notes = Array.isArray(figure.notes)
    ? figure.notes.filter((note) => typeof note === "string" && note.trim().length > 0)
    : [];
  if (notes.length < 2) problems.push("fewer than two stated assumptions");

  // A figure without its data is not a figure, and the renderers assume the
  // shape their mark needs. Refuse here rather than throwing at render.
  if (figure.kind === CHART.SANKEY) {
    const flows = Array.isArray(figure.flows) ? figure.flows : [];
    if (flows.length === 0) problems.push("no flows");
    if (flows.some((f) => !Number.isFinite(f?.value) || f.value < 0)) {
      problems.push("a flow with a missing or negative value");
    }
    const sides = [new Set(flows.map((f) => f?.from)), new Set(flows.map((f) => f?.to))];
    if (sides.some((side) => side.size > 8)) {
      problems.push("more than eight nodes a side, which nobody can follow");
    }
  } else if (chartRule(figure.kind)) {
    const points = Array.isArray(figure.points) ? figure.points : [];
    if (points.length === 0) problems.push("no points");
    // Every drawn value has to be a finite, non-negative number, in every
    // declared series: the renderers compute heights, coordinates and
    // opacity from these, and a missing, NaN, infinite or negative value
    // paints invalid or inverted geometry instead of refusing here.
    const seriesKeys =
      Array.isArray(figure.series) && figure.series.length ? figure.series : ["value"];
    const badValue = points.some((point) =>
      seriesKeys.some((key) => {
        const value = point?.[key];
        return !Number.isFinite(value) || value < 0;
      }),
    );
    if (points.length > 0 && badValue) {
      problems.push("a point with a missing, non-finite or negative value");
    }
    if (figure.kind === CHART.LINE && Array.isArray(figure.series) && figure.series.length > 3) {
      problems.push("more than three series on one scale");
    }
    if (figure.kind === CHART.STACKED && !Array.isArray(figure.series)) {
      problems.push("a stacked bar with no series");
    }
  }
  return problems;
}
