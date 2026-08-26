// Bring a dataset to the shelf.
//
// The subscriber's own upload, beside the published collections. Connected,
// the file goes to the platform and the card says it is published; standalone
// it is parsed here and kept in this browser, and the card says that instead.
// One component either way — features/grove/datasets.js owns which path runs.
import { useCallback, useEffect, useRef, useState } from "react";

import { isConnected } from "../../config.js";
import {
  addDataset,
  datasetCsv,
  listDatasets,
  removeDataset,
} from "../../features/grove/datasets.js";
import { EVENT, track, trackError } from "../../features/grove/telemetry.js";
import { PRESS_FIGURES } from "../../components/grove/pressFigures";

function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

function DatasetCard({ dataset, onRemove }) {
  const uploaded = new Date(dataset.uploadedAt);
  const when = Number.isNaN(uploaded.getTime())
    ? ""
    : uploaded.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  const take = async () => {
    try {
      saveBlob(await datasetCsv(dataset), dataset.fileName || `${dataset.id}.csv`);
    } catch (error) {
      trackError(error, { at: "datasetDownload" });
    }
  };
  return (
    <div className="gvc-fig cp-up__card">
      <span className="gvc-fig__cap">
        {dataset.name} · {dataset.published ? "On your shelf" : "In this browser"}
      </span>
      {dataset.points ? (
        <PRESS_FIGURES.bars points={dataset.points} />
      ) : (
        <p className="cp-up__shape">
          {(dataset.rowCount ?? 0).toLocaleString("en-US")} rows ·{" "}
          {dataset.columns ?? dataset.header?.length ?? 0} columns
          {dataset.header ? (
            <>
              <br />
              <span className="cp-up__cols">{dataset.header.join(" · ")}</span>
            </>
          ) : null}
        </p>
      )}
      <div className="gvc-fig__acts">
        <button type="button" className="gv-btn gv-btn--primary" onClick={take}>
          <span aria-hidden="true">&#8595;</span> Download
        </button>
        <button type="button" className="gv-btn gv-btn--quiet" onClick={() => onRemove(dataset.id)}>
          Remove
        </button>
      </div>
      <p className="cp-figmeta">
        {dataset.fileName} · {(dataset.rowCount ?? 0).toLocaleString("en-US")} rows
        {dataset.truncated ? " (preview keeps the first 500)" : ""}
        {when ? ` · added ${when}` : ""}
        {dataset.published ? "" : " · not published"}
      </p>
    </div>
  );
}

export default function PressDatasets() {
  const inputRef = useRef(null);
  const [datasets, setDatasets] = useState([]);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const connected = isConnected();

  const reload = useCallback(async (signal) => {
    try {
      const list = await listDatasets({ signal });
      setDatasets(list);
    } catch (err) {
      if (err?.name === "AbortError") return;
      trackError(err, { at: "datasetList" });
      setError("Your datasets could not be loaded.");
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      await reload(controller.signal);
    })();
    return () => controller.abort();
  }, [reload]);

  const takeFile = async (file) => {
    setError(null);
    if (!file) return;
    if (!/\.csv$/i.test(file.name)) {
      setError("The shelf takes CSV files. Export your table as .csv and try again.");
      return;
    }
    setBusy(true);
    try {
      // The text is read here either way: connected, the platform validates
      // the file it receives, but a file that does not parse should fail in
      // front of the person who chose it rather than after a round trip.
      const text = await file.text();
      const saved = await addDataset({ file, text, now: new Date() });
      track(EVENT.datasetUploaded, { published: Boolean(saved.published), rows: saved.rowCount });
      await reload();
    } catch (err) {
      track(EVENT.datasetUploadFailed, { code: err?.code });
      setError(err?.message || "That file could not be added.");
    } finally {
      setBusy(false);
    }
  };

  const drop = async (id) => {
    try {
      await removeDataset(id);
      await reload();
    } catch (err) {
      trackError(err, { at: "datasetRemove" });
      setError("That dataset could not be removed.");
    }
  };

  return (
    <section className="cp-sec cp-up" id="your-data" aria-label="Your datasets">
      <span className="cp-sec__band">Your data</span>
      <div className="cp-up__in">
        <div className="cp-up__say">
          <h2 className="cp-cedar__title">Bring a dataset to the shelf.</h2>
          <p className="cp-up__lede">
            Upload a CSV and it appears below with the same treatment as a collection: a figure
            where the first two columns are labels and numbers, the rows a download away.
            {connected
              ? " It is held with your subscription, and everyone on it sees the same shelf."
              : " This deployment is not connected to the platform, so the file stays in this browser and is not published."}
          </p>
        </div>
        <div
          className={dragging ? "cp-drop cp-drop--over" : "cp-drop"}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            takeFile(event.dataTransfer.files?.[0]);
          }}
        >
          <p className="cp-drop__text">{busy ? "Adding" : "Drop a CSV here, or"}</p>
          <button
            type="button"
            className="gv-btn gv-btn--primary"
            disabled={busy}
            onClick={() => inputRef.current?.click()}
          >
            Choose a file
          </button>
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            className="cp-drop__input"
            aria-label="Upload a CSV dataset"
            onChange={(event) => {
              takeFile(event.target.files?.[0]);
              event.target.value = "";
            }}
          />
          {error ? <p className="cp-gate__error" role="alert">{error}</p> : null}
        </div>
      </div>
      {datasets.length ? (
        <div className="cp-up__grid">
          {datasets.map((dataset) => (
            <DatasetCard key={dataset.id} dataset={dataset} onRemove={drop} />
          ))}
        </div>
      ) : null}
    </section>
  );
}
