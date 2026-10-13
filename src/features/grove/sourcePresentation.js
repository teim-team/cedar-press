// Presentation of permitted source facts. Ingest filenames never establish a publisher.
// Release/row eligibility is checked by the caller before this projection.
import registeredSources from "../../../data/cedar/source_display.json" with { type: "json" };
import presentation from "../../../data/cedar/source_presentation.json" with { type: "json" };
const SPECS = presentation.collections;
const PLOT_SOURCES = presentation.plot_sources;

const hasControl = (value) => [...value].some((character) => character.codePointAt(0) < 32);

function text(value) {
  if (typeof value === "number" && Number.isSafeInteger(value)) return String(value);
  return typeof value === "string" && value.trim() && value.length <= 2000
    && !hasControl(value) && !/[A-Za-z]:[\\/]|file:\/\/|\\\\/.test(value) ? value.trim() : null;
}

/** Public citation links only; a valid official CSV/PDF URL is still a citation. */
export function safeSourceUrl(value) {
  if (typeof value !== "string" || hasControl(value) || /[\s\\]/.test(value)) return null;
  try {
    const url = new URL(value);
    const host = url.hostname.toLowerCase();
    if (!["http:", "https:"].includes(url.protocol) || url.username || url.password
      || !host.includes(".") || host === "localhost" || /\.(localhost|local|internal|test|invalid)$/.test(host)
      || /^[\d.]+$/.test(host) || host.includes(":")) return null;
    if ([...url.searchParams.keys()].some((key) => /^(api[_-]?key|access[_-]?token|token|password|signature|sig|credential|x-amz-.*)$/i.test(key))) return null;
    return url.href;
  } catch { return null; }
}

function sourceTitle(value) {
  const title = text(value);
  return title && !/^[A-Za-z]:[\\/]|^[/\\]|\.(csv|parquet|jsonl?|xlsx?|zip|pdf)$/i.test(title) ? title : null;
}

/** Input is the already filtered public row, never internal evidence or a source contract. */
export function sourcePresentation(collection, row, recordUrl) {
  const spec = SPECS[collection];
  if (!spec || collection === "gaming") return null;
  // Owner ruling 2026-10-04 (Elijah Moreno): a row's review or rights status is
  // provenance; it no longer suppresses the row's source citation.
  const family = collection === "plot" ? PLOT_SOURCES[text(row.source_id)] : null;
  const registered = registeredSources.sources[`${collection}/${text(row.source_id)}`];
  const identifiedPublisher = family?.[0] ?? registered?.publisher ?? spec.publisher ?? spec.systems?.[text(row.source_system)] ?? null;
  const title = family?.[1] ?? sourceTitle(row[spec.title]) ?? registered?.source_title ?? spec.dataset ?? null;
  const url = safeSourceUrl(collection === "plot" ? row.source_record_url : null) ?? safeSourceUrl(recordUrl);
  const publisher = identifiedPublisher ?? (url ? presentation.publishers_by_host?.[new URL(url).hostname] : null) ?? null;
  const issuingAuthority = (spec.issuingAuthorityFields ?? []).map((name) => sourceTitle(row[name])).find(Boolean) ?? null;
  const fields = (names) => Object.fromEntries((names ?? []).flatMap((name) => text(row[name]) ? [[name, text(row[name])]] : []));
  const reportingPeriod = fields(spec.periods);
  const eventDates = fields(spec.events);
  const locators = fields(spec.locators);
  const gaps = [];
  if (!publisher) gaps.push("Original publisher has not been established for this record.");
  const titleBasis = family ? "Source dataset title" : spec.titleBasis ?? (registered ? "Registered source title" : "Source dataset");
  if (!title || titleBasis === "Cedar event description" || titleBasis === "Registered source title") gaps.push("Original report or page title is not recorded.");
  if (!url) gaps.push("A public source URL is not recorded.");
  if (collection === "plot" && !safeSourceUrl(row.source_record_url)) gaps.push("A dataset or query link does not establish a citation to the individual parent record.");
  const periodText = Object.entries(reportingPeriod).map(([key, value]) => `${key.replaceAll("_", " ")}: ${value}`).join("; ");
  const originalDocumentSha256 = (spec.documentHashFields ?? []).map((name) => row[name])
    .find((value) => typeof value === "string" && /^[a-f0-9]{64}$/.test(value)) ?? null;
  const retrievedDate = (spec.retrievedFields ?? []).map((name) => text(row[name])).find(Boolean) ?? null;
  // The kind of evidence behind the record's link (NEED: a company page or a
  // federal identifier), so a reader can weigh the source.
  const basis = spec.evidenceBasis ? text(row[spec.evidenceBasis.field]) : null;
  return {
    ...(spec.evidenceBasis ? { evidenceBasis: basis ? { label: spec.evidenceBasis.label, text: basis } : null } : {}),
    publisher, issuingAuthority, title, titleBasis,
    url, reportingPeriod, periodText, eventDates, locators,
    publicationDate: (spec.publishedFields ?? [spec.published]).map((name) => text(row[name])).find(Boolean) ?? null,
    snapshotDate: text(row[spec.snapshot]),
    originalDocumentSha256, retrievedDate,
    citation: [publisher ?? "Publisher not established", issuingAuthority ? `Issued by: ${issuingAuthority}` : null, title ? `${titleBasis}: ${title}` : null, Object.values(locators).join("; ") || null, periodText || null, url].filter(Boolean).join(". "),
    gaps,
  };
}
