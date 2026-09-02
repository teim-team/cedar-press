# Codebook — Deals

*790 rows across 9 file(s). Generated 2026-08-07.*

Variables marked **internal** are retained for auditing and are not included in published extracts.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `Deal_ID` | text | code | 100% | Identifier. |
| `Event_Date` | text | YYYY-MM-DD | 100% | Date the transaction was announced or became effective. |
| `Event_Year` | integer | YYYY | 100% | Year. |
| `Event_Quarter` | text |  | 100% | One of: `Q4`, `Q2`, `Q3`, `Q1` |
| `Event_Month` | text | 1-12 | 100% | Month of the event. |
| `Deal_Title` | text | text | 100% | Short title of the transaction. |
| `Native_Party` | text | text | 100% | Native entity or Native-owned organisation in the transaction. |
| `Native_Party_Type` | text | category | 100% | Class of the Native party: entity, enterprise, nonprofit, or intertribal organisation. |
| `Counterparty_or_Funder` | text | text | 100% | The other party, or the funding agency. |
| `Deal_Category` | text | category | 100% | Transaction type. Federal awards and negotiated transactions are separate populations and must not be combined into one series. |
| `Industry` | text | category | 100% | Industry of the target or activity. |
| `Event_Type` | text | category | 100% | Nature of the event recorded. |
| `Status` | text | category | 100% | Whether the transaction was announced, completed, or terminated. |
| `Record_Scope` | text | category | 100% | Breadth of the record: a single transaction, or a programme covering several. |
| `Announced_Value_USD` | integer | USD, nominal | 94% | Announced transaction value. Blank when the parties did not disclose one - blank means undisclosed, never zero. |
| `Value_Type` | text | category | 100% | What the reported value measures. |
| `Project_Total_Value_USD` | integer | USD, nominal | 14% | Amount. |
| `State` | text | 2-letter code | 84% | US state or territory. |
| `Location` | text | text | 65% | Geography associated with the transaction. |
| `Description` | text | text | 100% | Narrative description of the transaction. |
| `Native_Connection` | text | text | 100% | How the Native party relates to the transaction. |
| `Source_1` | text | URL or citation | 100% | Primary published source for the record. |
| `Source_1_Type` | text | category | 100% | Kind of primary source. |
| `Source_2` | text | URL or citation | 75% | Corroborating source. |
| `Source_2_Type` | text | category | 75% | Kind of corroborating source. |
| `Verification_Status` | text | category | 100% | Whether the record's date and value were re-read in the retrieved source. |
| `Confidence` | text |  | 100% | One of: `High`, `Medium` |
| `Threshold_Exception` | text |  | 100% | One of: `No`, `Yes` |
| `Date_Basis` *(internal)* | text |  | 100% |  |
| `Notes` | text | text | 100% | Analyst notes on the record. |
| `Date_Added` | text |  | 100% | One of: `2026-08-05` |
| `Data_As_Of` | text |  | 100% | One of: `2026-08-05` |

## Value sets

- **`Event_Quarter`** — `Q4`, `Q2`, `Q3`, `Q1`
- **`Deal_Category`** — `Grant / public financing`, `Acquisition`, `Financing`, `Divestiture`, `Contract award`, `Commercial partnership`, `Real estate / land acquisition`, `Equity investment`, `Debt refinancing`, `Contract termination / buyout`, `Land transaction`, `Joint venture`, `Debt issuance`
- **`Status`** — `Awarded`, `Completed`, `Closed`, `Recommended for award`, `Announced`, `Closed/announced`, `Signed/announced`, `Allocated`, `Agreed`, `Committed`, `Rated; proposed at the date of the rating action`, `Proposed at the date of the rating action`, `Completed / announced`
- **`Verification_Status`** — `Primary verified`, `Verified`, `Primary + independent verified`, `Primary verified (rating agency press release)`, `Independent secondary corroborated`, `Secondary corroborated`, `Secondary verified`, `Needs federal award-ID verification`, `Primary verified (rating agency press releases, two independent actions)`
- **`Confidence`** — `High`, `Medium`
- **`Threshold_Exception`** — `No`, `Yes`
