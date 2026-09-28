import { useEffect, useState } from "react";
import { fetchReleaseCollections, fetchReleaseResearch, spreadsheetDownloadUrl } from "../../api.js";
import { researchComponents, researchFields, researchValue } from "../../features/grove/releaseResearch.js";
import SourceCitation from "./SourceCitation.jsx";

export function PlotGeometryPreview({ packet }) {
  const map = packet.map_preview;
  if (packet.collection !== "plot" || !map || map.release_id !== packet.release_id) return null;
  return <details><summary>Verified geometry examples ({map.features.length})</summary>
    <p>Representative source outlines in longitude and latitude. Each outline is fitted separately; sizes cannot be compared. These observations do not certify ownership or title.</p>
    <p>{map.omitted.length} selected rows have no drawable preview. Their unchanged source geometry remains in the verified download.</p>
    {map.outlines.map((outline) => <figure key={outline.id}>
      {outline.path ? <svg role="img" aria-label={`Source geometry ${outline.id}`} viewBox={outline.view_box} width="240" height="160" preserveAspectRatio="xMidYMid meet">
        <path d={outline.path} fill="currentColor" fillOpacity="0.3" fillRule="evenodd" stroke="currentColor" strokeWidth="1" vectorEffect="non-scaling-stroke" />
      </svg> : <p>This outline cannot be drawn without changing its geographic interpretation.</p>}
      <figcaption>{outline.id}. Bounds (west, south, east, north): {outline.bbox.join(", ")}.
        <SourceCitation source={outline.source} compact />
      </figcaption>
    </figure>)}
  </details>;
}

function ResearchRows({ collection, part }) {
  const [state, setState] = useState({ status: "loading", packet: null });
  useEffect(() => {
    const controller = new AbortController();
    fetchReleaseResearch(collection, part.releaseId, part.component, { signal: controller.signal })
      .then((packet) => { if (!controller.signal.aborted) setState({ status: "ready", packet }); })
      .catch(() => { if (!controller.signal.aborted) setState({ status: "unavailable", packet: null }); });
    return () => controller.abort();
  }, [collection, part.releaseId, part.component]);
  if (!state.packet) return <p role="status">{state.status === "loading" ? "Loading verified examples and definitions…" : "Verified examples are unavailable or held. No substitute rows are shown."}</p>;
  const packet = state.packet;
  const fields = researchFields(packet);
  return <>
    <p>{packet.sample_rows} real examples from {packet.source_rows.toLocaleString("en-US")} permitted observations of this record type. This sample does not establish complete collection coverage.</p>
    <PlotGeometryPreview packet={packet} />
    <div className="cp-ex__tablewrap" style={{ overflowX: "auto" }}>
      <table className="cp-ex__table"><thead><tr>{fields.map((field) => <th key={field.name}>{field.label || field.name}</th>)}<th>Original source and citation</th></tr></thead>
        <tbody>{packet.rows.map((selected) => <tr key={selected.release_row_sha256}>
          {fields.map((field) => <td key={field.name}>{researchValue(selected.row[field.name])}</td>)}
          <td><SourceCitation source={selected.source} /></td>
        </tr>)}</tbody>
      </table>
    </div>
    <details><summary>Variable definitions, missing values and aggregation</summary>
      <p>Row grain: {packet.codebook.row_grain}</p>
      {packet.codebook.aggregation_cautions.map((note) => <p key={note}>{note}</p>)}
      <dl>{fields.map((field) => <div key={field.name}><dt>{field.label || field.name} <code>{field.name}</code></dt>
        <dd>{field.definition || "Definition remains under research review."} Unit: {field.research_unit || field.unit || "Not specified"}.
          {field.temporal_meaning ? ` Time basis: ${field.temporal_meaning}.` : ""}
          {field.derivation ? ` Derivation: ${field.derivation}.` : ""}
          {field.missingness ? ` Missing: ${field.missingness.blank_or_null_rows} of ${field.missingness.release_rows} rows.` : ""}
        </dd></div>)}</dl>
    </details>
    <details><summary>Coverage and limitations</summary>
      {packet.limits.map((note) => <p key={note}>{note}</p>)}
    </details>
  </>;
}

export default function ReleasedCollections() {
  const [state, setState] = useState({ status: "loading", entries: [] });
  const [choice, setChoice] = useState("");
  const [opened, setOpened] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    fetchReleaseCollections({ signal: controller.signal }).then((result) => {
      if (!controller.signal.aborted) setState({ status: "ready", entries: (result.collections || []).filter((entry) => entry.id !== "gaming") });
    }).catch(() => { if (!controller.signal.aborted) setState({ status: "unavailable", entries: [] }); });
    return () => controller.abort();
  }, []);
  const entry = state.entries.find((item) => item.id === choice) || state.entries[0];
  const parts = researchComponents(entry);
  const spreadsheet = entry && spreadsheetDownloadUrl(entry.id, entry.spreadsheet, parts);
  return <section className="cp-sec" aria-label="Collection spreadsheets">
    <h2>Collection spreadsheets</h2>
    {!entry ? <p role="status">{state.status === "loading" ? "Checking this account’s datasets…" : "No verified dataset is available for this account."}</p> : <>
      <label>Collection <select value={entry.id} onChange={(event) => { setChoice(event.target.value); setOpened(null); }}>
        {state.entries.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
      </select></label>
      <h3>{entry.name}</h3>
      <p>A living dataset in one spreadsheet, preserving each observation's type, period and original source. Held records remain excluded.</p>
      {entry.updated ? <p>Updated {entry.updated}</p> : null}
      {spreadsheet ? <a href={spreadsheet}>Download spreadsheet</a> : <p role="status">The spreadsheet is not available for this account yet.</p>}
      {parts.some((part) => part.available) ? <details><summary>Examples, sources and definitions</summary>
        <label>Record type <select value={opened || ""} onChange={(event) => setOpened(event.target.value)}>
          <option value="" disabled>Choose records to inspect</option>
          {parts.filter((part) => part.available).map((part) => <option key={part.component || entry.id} value={part.component || entry.id}>{part.label}</option>)}
        </select></label>
        {parts.filter((part) => part.available && opened === (part.component || entry.id)).map((part) =>
          <ResearchRows key={`${entry.id}/${part.releaseId}/${part.component}`} collection={entry.id} part={part} />)}
      </details> : null}
    </>}
  </section>;
}
