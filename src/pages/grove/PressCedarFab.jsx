// REVIEW OWNER: Havala
//
// Cedar's floating launcher, on every Cedar Press page.
//
// The same markup the product renders (CedarWidget's launcher: status dot,
// label, surface context), with Cedar Press as the surface. The chat needs a
// signed-in session (cedarWidgetModel.shouldShowCedarWidget), so on the
// public pages the launcher goes to the app; when Cedar grows a public press
// surface this becomes the real widget with no other change.
//
// One component so every page carries it. It used to live only on the
// reader, and a launcher that comes and goes between pages reads as broken
// rather than absent.

import { appUrl } from "../../features/grove/appLink.js";

export function PressCedarFab() {
  return (
    <div className="cedar-widget cedar-widget--launcher-only">
      {/* The launcher says what the click does: it opens the app, where
          Ask Cedar lives. The old label promised to open Cedar for Cedar
          Press and delivered the dashboard, which is a control that lies;
          wiring the real widget with Press context into these standalone
          pages is the follow-up that retires this link. */}
      <a className="cedar-widget__launcher" href={appUrl("/app")} target="_blank" rel="noreferrer" aria-label="Open the app to ask Cedar">
        <span className="cedar-widget__status-dot" aria-hidden="true" />
        <span className="cedar-widget__launcher-copy">
          <span className="cedar-widget__launcher-label">Ask Cedar</span>
          <span className="cedar-widget__launcher-context">Opens the app</span>
        </span>
      </a>
    </div>
  );
}
