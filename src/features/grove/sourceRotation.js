/**
 * The labels the landing page's provenance band rotates through, and the
 * claim above them.
 *
 * NOT `PRESS_SOURCES`. That list is the source systems the released
 * collections name, each held to its evidence by `pressSources.test.js`, and
 * Methods and the door answer from it. This one describes Lumecon's sourcing
 * as a whole, across dataset construction and research, so it names systems
 * no single released Cedar Press collection reads (labor, parcel records).
 * Copy supplied by the owner, 2026-09-25, verbatim.
 *
 * The gaming sources (NIGC reports and opinions, sports wagering, casino
 * websites, gaming licenses, facility capacity, BIA gaming compacts, gaming
 * payment records and gaming litigation) were removed on the owner's note of
 * 2026-09-27: gaming is not a Cedar Press collection, so a panel on the Cedar
 * Press door should not name its sources. Nothing counts this list: the
 * marquee's run time is its length, and the 500+ figure never depended on it.
 *
 * The final six labels (parcel, assessor, permit and environmental-review
 * records) name the systems PLOT is being built from.
 */

export const SOURCE_REACH_CLAIM =
  "Lumecon uses trusted publicly available records and source metadata from 500+ distinct source websites in dataset construction and research.";

export const SOURCE_REACH_FIGURE = "500+";

export const SOURCE_ROTATION = Object.freeze([
  "USAspending contract awards",
  "FPDS contract awards feed",
  "SEC EDGAR filings",
  "ANCSA corporation filings",
  "Tribal newsrooms and trade reporting",
  "Federal agency award lists",
  "Federal Register documents",
  "Agency tribal consultation pages",
  "Dear Tribal Leader letters",
  "BLM NEPA ePlanning projects",
  "USAspending assistance transactions",
  "FAADS historical assistance records",
  "USAC E-Rate and Rural Health Care data",
  "BIA land-into-trust actions",
  "EPA environmental impact reviews",
  "Federal Audit Clearinghouse single audits",
  "OSHA injury and illness data",
  "DOL Form 5500 filings",
  "NLRB election records",
  "Census LODES employment data",
  "Lobbying Disclosure Act filings",
  "Regulations.gov public comments",
  "Congressional hearing records",
  "Congress.gov bills and actions",
  "House Clerk roll-call votes",
  "Senate roll-call votes",
  "Agency FOIA and correspondence logs",
  "FERC eLibrary dockets",
  "NRC public meeting records",
  "OIRA Executive Order 12866 meetings",
  "Interior IBIA and IBLA appeals",
  "Congressional earmark disclosures",
  "IRS Form 990 Schedule C",
  "National NAGPRA public databases",
  "ONRR monthly revenue",
  "ONRR fiscal-year disbursements",
  "ONRR production volumes",
  "Historical MMS Indian collections",
  "OSMRE Abandoned Mine Land distributions",
  "North Dakota tribal tax distributions",
  "North Dakota oil and gas tax series",
  "State tribal tax agreement reports",
  "Utah COBI and revitalization funds",
  "Montana oil and gas county distributions",
  "Osage Minerals Council payment history",
  "Resource asset source documents",
  "BTFA budget disclosures",
  "Parent-published Native company lists",
  "SBA and GSA certification records",
  "IRS Exempt Organizations Business Master File",
  "IRS Form 990 e-file returns",
  "IRS Form 990-N e-Postcard data",
  "Tribal government and enterprise directories",
  "SBA Dynamic Small Business Search",
  "FSRS subaward reporting",
  "BIA Realty/Tract Viewer",
  "Statewide parcel and cadastral GIS",
  "County parcel GIS",
  "County assessor and property-tax records",
  "Building permit and inspection records",
  "Environmental permits and CEQA reviews",
  // Cedar NEED's enrichments (owner, 2026-09-27). The 500+ figure is unchanged.
  "Patent records",
  "Rating-agency announcements",
]);
