import { useEffect, useState } from "react";
import { fetchReleaseCollections, fetchReleaseResearch, releaseDownloadUrl } from "../../api.js";
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
    <p>{packet.sample_rows} real examples from {packet.source_rows.toLocaleString("en-US")} permitted rows in this component. This sample does not establish complete collection coverage.</p>
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
    <details><summary>Release and provenance</summary><p>Release: <code>{packet.release_id}</code></p>
      <p>Manifest SHA-256: <code>{packet.provenance.manifest_file_sha256}</code></p>
      <p>Preview SHA-256: <code>{packet.provenance.sample_artifact_sha256}</code></p>
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
  return <section className="cp-sec" aria-label="Verified collection releases">
    <h2>Collection releases</h2>
    {!entry ? <p role="status">{state.status === "loading" ? "Checking this account’s releases…" : "No verified collection release is available for this account."}</p> : <>
      <label>Collection <select value={entry.id} onChange={(event) => { setChoice(event.target.value); setOpened(null); }}>
        {state.entries.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
      </select></label>
      <h3>{entry.name}</h3><p>Each component has its own grain and coverage. Held components remain excluded; a permitted subset is not the full collection.</p>
      {parts.length ? parts.map((part) => <div key={part.component || entry.id}>
        <h4>{part.label}</h4>
        {part.available ? <><p>{part.rows.toLocaleString("en-US")} permitted component rows</p>
          <a href={releaseDownloadUrl(entry.id, part.releaseId, part.component)}>Download verified JSONL</a>{" "}
          <button type="button" onClick={() => setOpened(part.component || entry.id)}>View real examples, sources and codebook</button>
          {opened === (part.component || entry.id) ? <ResearchRows key={`${entry.id}/${part.releaseId}/${part.component}`} collection={entry.id} part={part} /> : null}
        </> : <p>Held or unavailable. No permitted download or preview.</p>}
      </div>) : <p>No verified release is pinned for this collection.</p>}
    </>}
  </section>;
}
