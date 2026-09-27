/** One source display shared by real sample previews and the full record view. */
export default function SourceCitation({ source, compact = false }) {
  if (!source) return <span>Source details are unavailable.</span>;
  return (
    <div className="cp-rec__source">
      <strong>{source.publisher ?? "Publisher not established"}</strong>
      {source.issuingAuthority ? <span className="cp-rec__fine">Issued by: {source.issuingAuthority}</span> : null}
      {source.title ? <span className="cp-rec__fine">{source.titleBasis}: {source.title}</span> : null}
      {source.periodText ? <span className="cp-rec__fine">{source.periodText}</span> : null}
      {source.url ? <a href={source.url} target="_blank" rel="noreferrer">Open cited source <span aria-hidden="true">&#8599;</span></a> : null}
      {!compact ? <>
        {source.publicationDate ? <span className="cp-rec__fine">Published: {source.publicationDate}</span> : null}
        {source.snapshotDate ? <span className="cp-rec__fine">Source snapshot: {source.snapshotDate}</span> : null}
        {source.retrievedDate ? <span className="cp-rec__fine">Retrieved: {source.retrievedDate}</span> : null}
        {source.originalDocumentSha256 ? <span className="cp-rec__fine">Original document SHA-256: <code>{source.originalDocumentSha256}</code></span> : null}
        <p>{source.citation}</p>
        {source.gaps.map((gap) => <span className="cp-rec__fine" key={gap}>{gap}</span>)}
      </> : null}
    </div>
  );
}
