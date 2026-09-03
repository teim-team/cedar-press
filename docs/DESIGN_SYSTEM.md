# Cedar Press design system — the shared shell

The sitewide consistency contract: every page renders through these shared
pieces, and a page-local variant of any of them is a bug. Mapping of the
system's named components to where each lives today.

| Component | Implementation | Notes |
|---|---|---|
| SiteHeader + PrimaryNav | `PressMast` (`src/pages/grove/PressChrome.jsx`) | One masthead: logo, "Built by Lumecon… through Tribal Business News", nav (`NAV` array is the single source of section order/labels), account control. |
| PageContainer | `.cp` (`src/styles/grove/press.css`) | `--cp-measure: 1560px`, `padding-inline: 2.4rem` (1.15rem mobile). Articles keep a narrower *inner* prose measure; their hero, sponsorship and footer align to the outer grid. |
| SectionEyebrow | `.cp-sec__band` / `.cp-hero__access` | Small uppercase mono labels: `SECTIONS`, `ORIGINAL RESEARCH`, `SPONSORSHIP`. Three levels: eyebrow → major heading → mono metadata line. |
| ActionPill | `.cp-start__act` | The overview's start-here verbs. Reuse for any future inline CTA row; do not restyle per page. |
| SponsorshipUnit | `PressAd` + `AD_SLOT` (`pressAds.js`) | One component, shape variants per slot (banner on the overview, sidebar in articles). Same `SPONSORSHIP` cap, border, tint and CTA everywhere. Enquiries go to TBN's media kit (`AD_ENQUIRY_HREF`). |
| AskCedarFAB | `PressCedarFab` | Identical launcher, offset and dimensions on every page; context arrives via props (`examples`, `gated`) and events (`cedar:open`, `cedar:ask-collection`), never via per-page styling. |
| SiteFooter | `PressFoot` (`PressChrome.jsx`) | One footer, navy, full-bleed, thin teal top edge, nav left / publisher domains right — on every page including articles. `flush` only where the preceding band is already navy (the overview's close). |
| Breakpoints | `press.css` media queries | Stack points in use: 640 / 720 / 760 / 880 / 900 / 1000 / 1050 / 1250. New responsive work picks from these rather than inventing new ones. |
| Tokens | `redesign.css` `:root` vars | `--teal`, `--dteal`, `--ink`, `--line`, `--radius-card`, `--mono`, `--sans`; `--cp-measure` for the grid. Never hex-code a brand color in a page rule. |

Reference pages: the article template and the overview are the system's
anchors. When another page drifts, pull it toward those two, not the other
way around.
