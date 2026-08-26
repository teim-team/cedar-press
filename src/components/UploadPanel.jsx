// Add your data: the upload flow, mocked honestly.
//
// A subscriber picks a CSV, the browser parses it, and the dataset lands on a
// shelf below with the same card treatment as the launch collection — figure
// included when the first two columns read as label + number. Everything
// stays in this browser (localStorage) and the cards say so; publishing to
// the real shelf is the server work that lands with the pilot.
import { useRef, useState } from "react";

import { FIGURES } from "./figures.jsx";
import { addUpload, removeUpload, uploadCsv } from "../data/uploads.js";

function downloadBack(upload) {
  const blob = new Blob([uploadCsv(upload)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = upload.fileName;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

function UploadCard({ upload, onRemove }) {
  const uploaded = new Date(upload.uploadedAt);
  const when = Number.isNaN(uploaded.getTime())
    ? ""
    : uploaded.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  return (
    <div className="gvc-fig cp-upcard">
      <span className="gvc-fig__cap">{upload.name} · local preview</span>
      {upload.points ? (
        <FIGURES.bars points={upload.points} />
      ) : (
        <p className="cp-upcard__shape">
          {upload.rowCount.toLocaleString("en-US")} rows · {upload.header.length} columns
          <br />
          <span className="cp-upcard__cols">{upload.header.join(" · ")}</span>
        </p>
      )}
      <div className="gvc-fig__acts">
        <button type="button" className="gv-btn gv-btn--primary" onClick={() => downloadBack(upload)}>
          Download the data
        </button>
        <button type="button" className="gv-btn gv-btn--quiet" onClick={() => onRemove(upload.id)}>
          Remove
        </button>
      </div>
      <p className="cp-figmeta">
        {upload.fileName} · {upload.rowCount.toLocaleString("en-US")} rows
        {upload.truncated ? " (preview keeps the first 500)" : ""}
        {when ? ` · uploaded ${when}` : ""} · stored in this browser only
      </p>
    </div>
  );
}

export default function UploadPanel({ uploads, onChange }) {
  const inputRef = useRef(null);
  const [error, setError] = useState(null);
  const [dragging, setDragging] = useState(false);

  const takeFile = (file) => {
    setError(null);
    if (!file) return;
    if (!/\.csv$/i.test(file.name)) {
      setError("The preview takes CSV files. Export your table as .csv and try again.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      try {
        addUpload({ fileName: file.name, text: reader.result, now: new Date() });
        onChange();
      } catch (err) {
        setError(err?.message || "That file did not parse as a CSV.");
      }
    };
    reader.onerror = () => setError("The browser could not read that file.");
    reader.readAsText(file);
  };

  return (
    <section className="cp-sec" id="upload" aria-label="Add your data">
      <span className="cp-sec__band">Add your data</span>
      <div className="cp-upload">
        <div className="cp-upload__intro">
          <h2 className="cp-cedar__title">Bring a dataset to the shelf.</h2>
          <p className="cp-upload__lede">
            Upload a CSV and it appears below with the same treatment as the collection: a
            figure when the first two columns are labels and numbers, the rows a download
            away. In this preview the file stays in your browser; publishing to the shared
            shelf — with review, versioning and a citation trail — arrives with the pilot's
            server release.
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
          <p className="cp-drop__text">Drop a CSV here, or</p>
          <button type="button" className="gv-btn gv-btn--primary" onClick={() => inputRef.current?.click()}>
            Choose a file
          </button>
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            className="cp-drop__input"
            aria-label="Upload a CSV file"
            onChange={(event) => {
              takeFile(event.target.files?.[0]);
              event.target.value = "";
            }}
          />
          {error ? <p className="cp-gate__error" role="alert">{error}</p> : null}
        </div>
      </div>
      {uploads.length ? (
        <div className="cp-figs cp-upgrid">
          {uploads.map((upload) => (
            <UploadCard
              key={upload.id}
              upload={upload}
              onRemove={(id) => {
                removeUpload(id);
                onChange();
              }}
            />
          ))}
        </div>
      ) : null}
    </section>
  );
}
