import { StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";

// The stylesheets, once, in cascade order: the base (fonts and the element
// rules), the design system's tokens and the auth split, then the press
// pages' own rules, which are written under `.teim-rd` and re-pin the paper
// palette over the base. Every page used to import the three itself; the
// bundler deduplicated them, but the order was documented in one page of ten.
import "./index.css";
import "./styles/redesign.css";
import "./styles/grove/press.css";

import { AuthProvider } from "./context/AuthProvider.jsx";
import { startTelemetry } from "./features/grove/telemetry.js";
import {
  CedarPress,
  CedarPressArticle,
  CedarPressArticles,
  CedarPressData,
  CedarPressMethods,
  CedarPressPriorities,
  CedarPressResearchAccess,
  CedarPressSettings,
  CedarPressTribalRequest,
  CedarPressWhatsNew,
  PageArriving,
} from "./pages/grove/pages.jsx";
import { PageBoundary } from "./pages/grove/PageBoundary.jsx";
import {
  PRESS_ARTICLES_PATH,
  PRESS_ARTICLE_PATH,
  PRESS_DATA_PATH,
  PRESS_METHODS_PATH,
  PRESS_PATH,
  PRESS_REQUEST_PATH,
  PRESS_RESEARCH_PATH,
  PRESS_PRIORITIES_PATH,
  PRESS_SETTINGS_PATH,
  PRESS_WHATS_NEW_PATH,
} from "./features/grove/pressRoutes.js";

// Errors and performance go to Datadog when a deployment configures it;
// nothing is sent otherwise.
startTelemetry();

// The route table the app's App.jsx owns lives here in the standalone site:
// the reader at the root, the satellite pages on their own paths, and
// anything unknown back to the reader (whose gate is the front door).
createRoot(document.getElementById("root")).render(
  <StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <PageBoundary>
        <Suspense fallback={<PageArriving />}>
        <Routes>
          <Route path={PRESS_PATH} element={<CedarPress />} />
          <Route path={PRESS_ARTICLES_PATH} element={<CedarPressArticles />} />
          <Route path={PRESS_DATA_PATH} element={<CedarPressData />} />
          <Route path={PRESS_METHODS_PATH} element={<CedarPressMethods />} />
          <Route path={PRESS_REQUEST_PATH} element={<CedarPressTribalRequest />} />
          <Route path={PRESS_RESEARCH_PATH} element={<CedarPressResearchAccess />} />
          <Route path={PRESS_WHATS_NEW_PATH} element={<CedarPressWhatsNew />} />
          <Route path={PRESS_SETTINGS_PATH} element={<CedarPressSettings />} />
          <Route path={PRESS_PRIORITIES_PATH} element={<CedarPressPriorities />} />
          <Route path={PRESS_ARTICLE_PATH} element={<CedarPressArticle />} />
          <Route path="*" element={<Navigate to={PRESS_PATH} replace />} />
        </Routes>
        </Suspense>
        </PageBoundary>
      </BrowserRouter>
    </AuthProvider>
  </StrictMode>,
);
