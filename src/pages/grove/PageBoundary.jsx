/**
 * PURPOSE
 * What a reader sees when a page's code does not arrive.
 *
 * A lazy route's import rejects when the connection drops between clicks,
 * or when a tab left open navigates after a deployment has replaced the
 * hashed assets. Suspense handles only the wait; without a boundary React
 * unmounts the whole application and the reader gets a blank page (Codex,
 * PR #68). This catches it and offers the one action that helps: a reload,
 * which fetches the current assets.
 */
import { Component } from "react";

export class PageBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error) {
    // Errors and performance go to Datadog when configured; here, the
    // console is the record a developer reads.
    console.error("A page did not load", error);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="teim-rd teim-rd--paper" role="alert" style={{ minHeight: "60vh", display: "grid", placeItems: "center", padding: "2rem" }}>
        <div style={{ maxWidth: "36rem", textAlign: "center" }}>
          <p style={{ fontWeight: 600, margin: "0 0 0.5rem" }}>{this.props.what ?? "This page"} did not load.</p>
          <p style={{ margin: "0 0 1rem" }}>
            The connection dropped, or the site was updated while this tab was open. Reloading fetches it again.
          </p>
          <button type="button" className="gv-btn gv-btn--primary" onClick={() => window.location.reload()}>
            Reload
          </button>
        </div>
      </div>
    );
  }
}
