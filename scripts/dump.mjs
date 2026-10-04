// One parity export command for access rules, collection values and the Press catalog.
//   node scripts/dump.mjs --kind access|collection|press [--check] [--target path]
// Without --target the selected payload is printed; press --check uses its maintained snapshot.
import { readFileSync, writeFileSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { EXCLUDED_COLLECTIONS, COLLECTION_FIGURES, LAUNCH_COLLECTION, UNMEASURED_FIELDS,
  collectionCedarFacts, collectionCitation, collectionContextLine, collectionCsv,
  collectionFindings, collectionSample, collectionTables, figuresInShelfOrder,
  hasSample, samplePath } from "../src/features/grove/collection.js";
import { loadCodebook } from "../src/features/grove/codebook.js";
import { PLAN_REACH, SHELF, canOpenDataset, canReadCedarPress, shelfReach } from "../src/features/grove/pressAccess.js";
import { PRESS_CATALOG } from "../src/features/grove/pressCatalog.js";
import { WORKSPACE_TIERS } from "../src/workspaceTier.js";
import { PRESS_ARTICLES, TBN_URL, LUMECON_URL } from "../src/features/grove/pressArticles.js";
import { CITATIONS, REPORT_CITATION_HREF } from "../src/features/grove/pressCitations.js";
import { COLLECTION_JOBS, cedarQuestions } from "../src/features/grove/pressJobs.js";
import { PRESS_RELEASES } from "../src/features/grove/pressReleases.js";
import { WORK_KINDS } from "../src/features/grove/readerWork.js";
// The raw previews sit under the repository root (data/cedar/samples/), not public/.
const REPO_ROOT = fileURLToPath(new URL("..", import.meta.url)).replace(/\/$/, "");
const PRESS_TARGET = fileURLToPath(new URL("../server/cedar_press/_press_data.json", import.meta.url));

function accessPayload() {
// Every tier the product recognizes, not only the ones with a Press answer.
// A tier that reaches nothing is a value the Python side must also produce,
// and a dump that omitted it would let a new tier open the page on one side.
const TIERS = Object.keys(WORKSPACE_TIERS).sort();

const asUser = (tier) => ({ workspace_tier: tier });

const byShelf = {};
for (const entry of PRESS_CATALOG) {
  (byShelf[entry.shelf] ??= []).push(entry.id);
}
for (const ids of Object.values(byShelf)) ids.sort();

return {
      tiers: TIERS,
      shelves: SHELF,
      // The raw map, so a missing key is reported as a missing key rather
      // than only as a wrong answer for one tier.
      planReach: PLAN_REACH,
      // The resolved answers, which is what the two products actually have to
      // agree on. `shelfReach` folds in the unknown-tier fallback that
      // PLAN_REACH alone does not show.
      shelfReach: Object.fromEntries(TIERS.map((t) => [t, shelfReach(asUser(t))])),
      canReadCedarPress: Object.fromEntries(
        TIERS.map((t) => [t, canReadCedarPress(asUser(t))]),
      ),
      // The Press/Grove content split as the catalog states it. Compared
      // against the collections manifest, whose `excluded` entries carry the
      // shelf the Cedar data workspace assigned.
      catalogByShelf: Object.fromEntries(Object.entries(byShelf).sort()),
      // Catalog entries presented by their record structure (`coverage:
      // STRUCTURE`): live on their shelves and opened by plan, with no release
      // file. The launch collection holds only the ones with a release, so
      // the Python side compares the catalog minus these against it, and
      // holds this list to the manifest: structure exactly when there is no
      // release.
      structureOnly: PRESS_CATALOG.filter((entry) => entry.coverage?.kind === "structure").map((entry) => entry.id).sort(),
      // What the CLIENT decides, collection by collection, over the whole
      // catalog rather than the storefront subset. This is the decision the
      // browser acts on -- it is what puts a download control on a tile --
      // and until it was dumped nothing compared it to `may_open`. The shelf
      // maps above agreeing is not enough: `PRESS_CATALOG` carries a
      // collection the launch collection does not, so the two sides can hold
      // identical tier maps and still disagree about a specific tile.
      canOpen: Object.fromEntries(
        TIERS.map((tier) => [
          tier,
          PRESS_CATALOG.filter((entry) => canOpenDataset(asUser(tier), entry))
            .map((entry) => entry.id)
            .sort(),
        ]),
      ),
      excluded: EXCLUDED_COLLECTIONS.map((entry) => ({
        id: entry.id,
        shelf: entry.shelf,
      })),
    };
}

async function collectionPayload() {
// The same fixed date on both sides. `collectionCitation` takes the accessed
// date as an argument precisely so neither implementation reads a clock, which
// is what would make this comparison flap at midnight.
const ACCESSED = "1 January 2026";

// collectionCsv checks a spreadsheet sample against the codebook, which the
// browser loads on demand (src/features/grove/codebook.js); load it here too.
await loadCodebook();
const csvs = {};
for (const dataset of LAUNCH_COLLECTION) {
  if (!hasSample(dataset.id)) {
    csvs[dataset.id] = null;
    continue;
  }
  const text = await readFile(`${REPO_ROOT}${samplePath(dataset.id)}`, "utf8");
  csvs[dataset.id] = collectionCsv(dataset.id, text);
}

const findings = collectionFindings();

return {
      launchCollection: LAUNCH_COLLECTION,
      unmeasuredFields: UNMEASURED_FIELDS,
      excluded: EXCLUDED_COLLECTIONS,
      contextLine: collectionContextLine(),
      figures: COLLECTION_FIGURES,
      figureOrder: figuresInShelfOrder().map((figure) => figure.id),
      findings: {
        // `requires` is a list of `{label}` objects here and a list of strings
        // in Python: the JavaScript shape is what FindingsPanel renders and
        // the Python one is what a dataclass can hold. Flattened to the label
        // so the comparison is of the content rather than of two renderers'
        // conveniences -- the one place the two shapes legitimately differ,
        // named here rather than silently skipped.
        supported: findings.supported,
        needs: findings.needs,
        narratives: findings.narratives.map((lead) => ({
          ...lead,
          requires: lead.requires.map((item) => item.label),
        })),
      },
      citations: Object.fromEntries(
        LAUNCH_COLLECTION.map((d) => [d.id, collectionCitation(d.id, ACCESSED)]),
      ),
      citationsWithoutDate: Object.fromEntries(
        LAUNCH_COLLECTION.map((d) => [d.id, collectionCitation(d.id)]),
      ),
      unknownIdCitation: collectionCitation("not-a-collection"),
      cedarFacts: Object.fromEntries(
        LAUNCH_COLLECTION.map((d) => [d.id, collectionCedarFacts(d.id)]),
      ),
      samples: Object.fromEntries(LAUNCH_COLLECTION.map((d) => [d.id, collectionSample(d.id)])),
      tables: Object.fromEntries(LAUNCH_COLLECTION.map((d) => [d.id, collectionTables(d.id)])),
      csvs,
    };
}

function pressPayload() {
return {
      tbnUrl: TBN_URL,
      lumeconUrl: LUMECON_URL,
      articles: PRESS_ARTICLES,
      citations: CITATIONS,
      reportCitationHref: REPORT_CITATION_HREF,
      catalog: PRESS_CATALOG,
      releases: PRESS_RELEASES,
      // The vocabulary /press/profile accepts, so the service and the
      // Settings page cannot disagree about what a reader may say they do.
      workKinds: WORK_KINDS,
      // Cedar's suggested questions, by collection, each with the profile
      // branch it must land in. Not served: the Python suite runs every one
      // through `answer_from_profile`, so a suggestion the router would
      // refuse or misroute fails a build instead of reaching a reader.
      cedarQuestions: Object.fromEntries(Object.keys(COLLECTION_JOBS).map((id) => [id, cedarQuestions(id)])),
    };
}

export function parseDumpArguments(argv) {
  const result = { kind: null, check: false, target: null };
  const seen = new Set();
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    if (!["--kind", "--check", "--target"].includes(key) || seen.has(key)) {
      throw new Error("Use --kind access|collection|press [--check] [--target path].");
    }
    seen.add(key);
    if (key === "--check") result.check = true;
    else {
      const value = argv[++i];
      if (!value || value.startsWith("--")) throw new Error(key + " requires a value.");
      result[key.slice(2)] = value;
    }
  }
  if (!["access", "collection", "press"].includes(result.kind)) throw new Error("Choose --kind access, collection or press.");
  if (result.check && !result.target && result.kind !== "press") throw new Error("--check requires --target for access or collection.");
  return result;
}

export async function renderDump(kind) {
  let payload;
  if (kind === "access") payload = accessPayload();
  else if (kind === "collection") payload = await collectionPayload();
  else if (kind === "press") payload = pressPayload();
  else throw new Error("Unknown dump kind.");
  return JSON.stringify(payload, null, 2) + (kind === "press" ? "\n" : "");
}

export async function main(argv) {
  const options = parseDumpArguments(argv);
  const text = await renderDump(options.kind);
  const target = options.target ? resolve(options.target) : PRESS_TARGET;
  if (options.check) {
    let held = null;
    try { held = readFileSync(target, "utf8"); } catch (error) { if (error.code !== "ENOENT") throw error; }
    if (held !== text) {
      process.stderr.write("Dump target is stale or missing: " + target + ". Regenerate with node scripts/dump.mjs --kind " + options.kind + " --target <path>.\n");
      return 1;
    }
    process.stdout.write("  " + options.kind + " dump current\n");
  } else if (options.target) writeFileSync(target, text);
  else process.stdout.write(text);
  return 0;
}
if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  try { process.exitCode = await main(process.argv.slice(2)); }
  catch (error) { process.stderr.write(error.message + "\n"); process.exitCode = 2; }
}
