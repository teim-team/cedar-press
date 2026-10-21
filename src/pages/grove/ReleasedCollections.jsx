import { useEffect, useState } from "react";
import { fetchReleaseCollections, fetchReleaseResearch, isUnreachable, spreadsheetDownloadUrl } from "../../api.js";
import { researchComponents, researchFields, researchValue, spreadsheetRecordCount } from "../../features/grove/releaseResearch.js";
import SourceCitation from "./SourceCitation.jsx";

export function PlotGeometryPreview({ packet }) {
  const map = packet.map_preview;
  if (packet.collection !== "plot" || !map || map.release_id !== packet.release_id) return null;
  return <details><summary>Geometry examples ({map.features.length})</summary>
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
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    fetchReleaseResearch(collection, part.releaseId, part.component, { signal: controller.signal })
      .then((packet) => { if (!controller.signal.aborted) setState({ status: "ready", packet }); })
      .catch((error) => { if (!controller.signal.aborted) setState({ status: isUnreachable(error) ? "unreachable" : "unavailable", packet: null }); });
    return () => controller.abort();
  }, [collection, part.releaseId, part.component, attempt]);
  const retry = () => {
    setState({ status: "loading", packet: null });
    setAttempt((n) => n + 1);
  };
  if (!state.packet) return <p role="status">{state.status === "loading" ? "Loading examples and definitions…"
    : state.status === "unreachable" ? <>The examples could not be reached. <button type="button" className="cp-retry" onClick={retry}>Retry</button></>
      : "Examples are unavailable for this account."}</p>;
  return <ResearchPreview packet={state.packet} />;
}

export function ResearchPreview({ packet }) {
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
  // A Retry is a new attempt. "unreachable" (no answer in time, or no
  // connection) is kept apart from "unavailable" (the service answered and
  // refused): only the second says something about this account.
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    fetchReleaseCollections({ signal: controller.signal }).then((result) => {
      if (!controller.signal.aborted) setState({ status: "ready", entries: (result.collections || []).filter((entry) => entry.id !== "gaming") });
    }).catch((error) => { if (!controller.signal.aborted) setState({ status: isUnreachable(error) ? "unreachable" : "unavailable", entries: [] }); });
    return () => controller.abort();
  }, [attempt]);
  const retry = () => {
    setState({ status: "loading", entries: [] });
    setAttempt((n) => n + 1);
  };
  const entry = state.entries.find((item) => item.id === choice) || state.entries[0];
  const parts = researchComponents(entry);
  const recordCount = spreadsheetRecordCount(entry);
  const spreadsheet = entry && spreadsheetDownloadUrl(entry.id, entry.spreadsheet, parts);
  const notice = {
    loading: "Checking this account\u2019s collections\u2026",
    unreachable: "The collections could not be reached. Check the connection and try again.",
    unavailable: "Collections are not available for this account right now.",
  }[state.status] ?? "No collections have been published for this account yet.";
  return <section className="cp-sec cp-rel" aria-label="Collections">
    <h1 className="cp-rel__title">Collections</h1>
    {!entry ? <div className="cp-rel__card cp-rel__card--empty" role="status" aria-busy={state.status === "loading"}>
      <p>{notice}</p>
      {state.status === "unreachable" ? <button type="button" className="cp-btn cp-btn--primary" onClick={retry}>Retry</button> : null}
    </div> : <div className="cp-rel__grid">
      <nav className="cp-rel__rail" aria-label="Collections">
        <ul>{state.entries.map((item) => <li key={item.id}>
          <button type="button" aria-current={item.id === entry.id ? "true" : undefined}
            onClick={() => { setChoice(item.id); setOpened(null); }}>{item.name}</button>
        </li>)}</ul>
      </nav>
      <div className="cp-rel__card">
        <h2 className="cp-rel__name">{entry.name}</h2>
        <p className="cp-rel__lede">A living dataset in one spreadsheet, preserving each observation&rsquo;s type, period and original source. Each collection&rsquo;s About text says which records are not included.</p>
        <dl className="cp-rel__facts">
          {recordCount !== null ? <div><dt>Observations</dt><dd>{recordCount.toLocaleString("en-US")}</dd></div> : null}
          {entry.updated ? <div><dt>Updated</dt><dd>{entry.updated}</dd></div> : null}
        </dl>
        {recordCount !== null ? <p className="cp-rel__fine">Record types have distinct grains; combine amounts only as the codebook permits.</p> : null}
        {spreadsheet
          ? <a className="cp-btn cp-btn--primary" href={spreadsheet}>Download spreadsheet</a>
          : <p className="cp-rel__status" role="status">No spreadsheet release has been published for this collection yet.</p>}
        {parts.some((part) => part.available) ? <details className="cp-rel__more"><summary>Examples, sources and definitions</summary>
          <label>Record type <select value={opened || ""} onChange={(event) => setOpened(event.target.value)}>
            <option value="" disabled>Choose records to inspect</option>
            {parts.filter((part) => part.available).map((part) => <option key={part.component || entry.id} value={part.component || entry.id}>{part.label}</option>)}
          </select></label>
          {parts.filter((part) => part.available && opened === (part.component || entry.id)).map((part) =>
            <ResearchRows key={`${entry.id}/${part.releaseId}/${part.component}`} collection={entry.id} part={part} />)}
        </details> : null}
      </div>
    </div>}
  </section>;
}
