// Programmer: Elijah Moreno
// Purpose: To create preliminary figures for Ho-Chunk visit
// Originally drafted by ESM on 20230318
// Last edited: 20230326

version 17.0
set more off
set scheme tpg

do "~/Dropbox/Winnebago/WinnebagoGraphSetUpParameters.do"
do "~/Dropbox/tpgstataprograms/TPGColorMacros.do"

cd "~/Dropbox/Winnebago/ESM"

log using hcipreliminaryfigures, name(hcipreliminaryfigures) replace

/* NOTES

	Data comes from Just Sikren pulling raw data from FPDS-NG. The curated dataset
	one can download from going to the Winnebago Tribe of Nebraska's page 
	is less acurate than what I obtained. We have data going back to 1999 but 
	it appears that these obligations went to the tribe, that is to say Winnebago
	Tribe of Nebraska and not an HCI. It is also important to note that HCI 
	reported their first involvement in federal contracting came from subcontracting 
	dollars in 2004, at least for the All Native Group. 
	
	Subcontracting data wasn't available to download prior to 2010. So even 
	though we don't have subcontracting data before this, doesn't mean that 
	HCI didn't receive sub award obligations prior to this time it is only 
	now we can look at this
	
	Direct payments, such as funds associated with IHS 638 contracts is 
	obtained here: https://www.usaspending.gov/award/ASST_NON_56G180126_7527
	
	Note that BGOV and HigherGov do not collect "Direct Payments" which is 
	what the 638 funding is classified as. Not a contract.

*/

global inflationfactor          0 // Uses fred key to create inflation 
global ihs638                   0 // Cleans up raw ihs 638 data
global idv                      0 // Cleans up raw idv data
global rawfpds                  0 // Cleans up raw fpds prime data
global rawfsrs                  0 // Cleans up raw fsrs sub data 
global primetrends              1 // Prime award dollars over time 
global subtrends                1 // Sub award dollars over time 
global idvtrends                1 // IDV award dollars over time 
global totaltrends              1 // Combined prime, sub and idv obligations over time 
global subsidiarydollars        1 // Dollars by HCI and subsidiaries
global setaside                 1 // Set-aside share
global growthsetaside           1 // Growth of dollars from key set-asides over time
global supersector              1 // Supersector composition civilian vs. defense
global supersectortrends        1 // trends for top five supersector

// 2022 trends
global totaltrends2022          1 // 2022
global subsidiarydollars2022    1 // 2022
global setaside2022             1 // 2022
global supersector2022          1 // 2022

// All funds 
global awardandcompact          1 // Combines all awards regardless of HCI or Tribe and also compact
global awardandcompact2022      1 // 2022
global awardandcompacttribe     1 // Combines all awards for Tribe and also compact
global awardtribe               1 // Combines all awards for Tribe

// place 
global placefunding             1 // obligations by place over time 
global placefunding8a           1 // obligations by place over time 8a only

if $inflationfactor==1{
	
	import fred CPIAUCSL, aggregate(annual,avg) clear //use -help fred- if it balks
	gen inflyear = year(daten)
	keep if inflyear <= 2022 //uses the year into which dollars will be denominated (see GraphSetUpParameters)
	sort inflyear
	gen inflfac =  CPI[_N]/CPI // Last year inflfac should be 1
	keep infl*
	save annualinflation, replace
	
} // inflationfactor

if $ihs638==1{
	
	import delimited "~/Dropbox/Winnebago/ESM/raw/Assistance_56G180126_TransactionHistory_1.csv", clear 

	rename federal_action_obligation ihs638_transaction_value
	
	rename action_date_fiscal_year year
	
	rename recipient_name awardeename
	
	replace awardeename = "Winnebago Tribe of Nebraska" if awardeename == "WINNEBAGO TRIBE OF NEBRASKA"	
	
	gen tribe_recipient = 0
	replace tribe_recipient = 1 if awardeename == "Winnebago Tribe of Nebraska"
	
	label var tribe_recipient "Tribe was direct recipient of awards not HCI"
	sort year 
	
	drop if year == 2023
	
	gen inflyear = year 
	merge m:1 inflyear using annualinflation , keep(3) nogen
	
	gen i_ihs638_transaction_value = inflfac*ihs638_transaction_value
	label var i_ihs638_transaction_value "value of transaction in 2022 dollars"
	
	gen i_total_obligated_amount = inflfac*total_obligated_amount
	label var i_total_obligated_amount "Total value of contract in 2022 dollars"
	
	rename recipient_uei awardee_uei
	
	save "~/Dropbox/Winnebago/ESM/clean/ihs file.dta", replace
	
} // ihs638


if $idv==1{
	
	import excel "~/Dropbox/Winnebago/ESM/raw/Data Request 3-20.xlsx", sheet("Raw IDV FPDS") firstrow case(lower) clear

	// renaming for ease of interpretation
	rename action_date_fiscal_year year
	rename federal_action_obligation idv_transaction_value
	rename awardid contractnumber
	rename award_agency_name funding_agency
	rename naics_code naics
	rename type_of_set_aside typeofsetaside
	rename uei_legal_business_name awardeename // this has the most observations for names 
	
	label var year "Year unique transaction occured"
	label var idv_transaction_value "Nominal value of transaction"
	label var total_dollars_obligated "Total nominal value of contract"
	label var funding_agency "Agency who awarded contract"
	label var naics "Six Digit NAICS Code"
	
	order contractnumber year awardeename ultimate_parent_uei_name idv_transaction_value total_dollars_obligated typeofsetaside funding_agency period_of_performance_start_date number_of_offers_received
	
	// cleaning up string variables 
	
	replace awardeename = proper(awardeename)
	replace awardeename = itrim(awardeename) // remove any potential empty space at end of awardee name
	replace awardeename = trim(awardeename)  // remove any potential empty space at other end of awardee name
	
	replace ultimate_parent_uei_name = proper(ultimate_parent_uei_name)
	replace ultimate_parent_uei_name = itrim(ultimate_parent_uei_name) // remove any potential empty space at end of string
	replace ultimate_parent_uei_name = trim(ultimate_parent_uei_name)  // remove any potential empty space at other end of string
	
	replace funding_agency = proper(funding_agency)
	replace funding_agency = itrim(funding_agency) // remove any potential empty space at end of string
	replace funding_agency = trim(funding_agency)  // remove any potential empty space at other end of string
	
	replace number_of_offers_received = itrim(number_of_offers_received) // remove any potential empty space at end of string
	replace number_of_offers_received = trim(number_of_offers_received)  // remove any potential empty space at other end of string
	replace number_of_offers_received = "" if number_of_offers_received == "NULL"
	destring number_of_offers_received, replace
	
	replace awardeename = "Winnebago Tribe of Nebraska" if awardeename == "Winnebago Tribe Of Nebraska (9962)" | awardeename == "Winnebago Tribe Of Nebraska" | awardeename == "Little Priest Tribal College"	
	
	gen tribe_recipient = 0
	replace tribe_recipient = 1 if awardeename == "Winnebago Tribe of Nebraska"
	
	label var tribe_recipient "Tribe was direct recipient of awards not HCI"
	
	order  awardeename uei_id contractnumber year ultimate_parent_uei_name idv_transaction_value total_dollars_obligated typeofsetaside funding_agency period_of_performance_start_date number_of_offers_received
	
	// SUPERECTOR 
	// there are some NAICS that are less than 6 digits, making null
	replace naics = "" if length(naics) < 6
	
	// two digit naics = sector
	gen sector = substr(naics,1,2)
	
	// creating supersector categories 
	// from bls https://www.bls.gov/sae/additional-resources/naics-supersectors-for-ces-program.htm
	
	gen supersector = ""
	replace supersector = "Natural Resources & Mining" if sector == "21"
	replace supersector = "Construction" if sector == "23"
	replace supersector = "Manufacturing" if sector == "31" | sector == "32" |sector == "33"
	replace supersector = "Trade, Transportation, & Utilities" if sector == "42" | sector == "44" |sector == "45" | sector == "48" |sector == "49" |sector == "22"
	replace supersector = "Information" if sector == "51"  
	replace supersector = "Financial Activities" if sector == "52" | sector == "53" 
	replace supersector = "Professional & Business Services" if sector == "54" | sector == "55" |sector == "56" 
	replace supersector = "Education & Health Services" if sector == "61" | sector == "62" 
	replace supersector = "Leisure & Hospitality" if sector == "71" | sector == "72" 
	replace supersector = "Other services or Not given" if sector == "." | sector == "81" | sector == "91" | sector == "92" | sector == "93" | sector == ""
	
	gen defense = 0
	replace defense = 1 if funding_agency == "DEPT OF DEFENSE"
	
	label var defense "Defense contract or DoD is top level funding agency"
	
	sort year 
	
	drop if year == 2023
	
	gen inflyear = year 
	merge m:1 inflyear using annualinflation , keep(3) nogen
	
	gen i_idv_transaction_value = inflfac*idv_transaction_value
	label var i_idv_transaction_value "value of transaction in 2022 dollars"
	
	gen i_total_dollars_obligated = inflfac*total_dollars_obligated
	label var i_total_dollars_obligated "Total value of contract in 2022 dollars"
	
	label var sector "2 digit NAICS code"
	label var supersector "BLS Supersectors"
	
	keep awardeename uei_id contractnumber year ultimate_parent_uei_name idv_transaction_value total_dollars_obligated typeofsetaside funding_agency period_of_performance_start_date number_of_offers_received naics sector defense inflyear i_idv_transaction_value i_total_dollars_obligated tribe_recipient
	
	rename uei_id awardee_uei
	
	save "~/Dropbox/Winnebago/ESM/clean/idv file.dta", replace
	
} // idv

if $rawfpds==1{
	
	import excel "~/Dropbox/Winnebago/ESM/raw/Data Request 3-20.xlsx", sheet("Raw Prime Award FPDS") firstrow case(lower) clear
	
	// renaming for ease of interpretation
	rename action_date_fiscal_year year
	rename federal_action_obligation transaction_value
	rename awardid contractnumber
	rename award_agency_name funding_agency
	rename naics_code naics
	rename type_of_set_aside typeofsetaside
	rename uei_legal_business_name awardeename // this has the most observations for names 
	rename ip performance_state_name
	rename ir performance_country_name
	
	label var year "Year unique transaction occured"
	label var transaction_value "Nominal value of transaction"
	label var total_dollars_obligated "Total nominal value of contract"
	label var funding_agency "Agency who awarded contract"
	label var naics "Six Digit NAICS Code"
	
	/* DIFFERENCE IN DATES 
	
	the variable "period_of_performance_start_date" is when the contract was scheduled to begin
	while the year (originally action_date) is when a specific transaction/obligation occured
	
	so if you are interested in when money is exchanged use the year variable and associated transaction_value 
	if you are interested in contract start dates, yse period_of_performance_start_date
	
	*/
	
	order contractnumber year awardeename ultimate_parent_uei_name transaction_value total_dollars_obligated typeofsetaside funding_agency period_of_performance_start_date number_of_offers_received
	
	// cleaning up string variables 
	
	replace awardeename = proper(awardeename)
	replace awardeename = itrim(awardeename) // remove any potential empty space at end of awardee name
	replace awardeename = trim(awardeename)  // remove any potential empty space at other end of awardee name
	
	replace ultimate_parent_uei_name = proper(ultimate_parent_uei_name)
	replace ultimate_parent_uei_name = itrim(ultimate_parent_uei_name) // remove any potential empty space at end of string
	replace ultimate_parent_uei_name = trim(ultimate_parent_uei_name)  // remove any potential empty space at other end of string
	
	replace funding_agency = proper(funding_agency)
	replace funding_agency = itrim(funding_agency) // remove any potential empty space at end of string
	replace funding_agency = trim(funding_agency)  // remove any potential empty space at other end of string
	
	replace number_of_offers_received = itrim(number_of_offers_received) // remove any potential empty space at end of string
	replace number_of_offers_received = trim(number_of_offers_received)  // remove any potential empty space at other end of string
	replace number_of_offers_received = "" if number_of_offers_received == "NULL"
	destring number_of_offers_received, replace
	
	replace awardeename = "All Native Solutions Corporation" if awardeename == "Allnative Solutions Corporation"
	replace awardeename = "All Native Systems LLC" if awardeename == "All Native Systems Llc"
	replace awardeename = "All Native Systems LLC" if awardeename == "All Native Systems, L.L.C."
	replace awardeename = "All Native, Inc." if awardeename == "All Native"
	replace awardeename = "Blue Earth Marketing Company" if awardeename == "Blue Earth Marketing"
	replace awardeename = "Dynamic Systems, Inc" if awardeename == "Dynamic Systems, Inc." 
	replace awardeename = "HCI Management Services Company" if awardeename == "Hci Management Services Company" 
	replace awardeename = "HCI Logistics Company" if awardeename == "Hci Logistics Company" 
	replace awardeename = "HCI Distribution Company" if awardeename == "Hci Distribution Company" 
	replace awardeename = "HCI Construction" if awardeename == "Hci Construction Company" | awardeename == "Hci Construction" | awardeename == "H C I Construction" 
	replace awardeename = "Protege Health Services LLC" if awardeename == "Protege Health Services Llc" | awardeename == "Protege Health Services, Llc"
	replace awardeename = "Wincomp LLC" if awardeename == "Wincomp L L C Dba All Native"
	replace awardeename = "Wincomp LLC" if awardeename == "Wincomp Llc"
	replace awardeename = "Wincomp LLC" if awardeename == "Wincomp Limited Liability Company"
	
	// dropping extraneous variables
	drop schema-last_modified_date award_agency_id-parent_award_modification_number
	drop action_date period_of_performance_current_en-period_of_performance_potential_
	drop base_and_exercised_options_value-non_governmental_dollars
	drop current_total_value_of_award-labor_standards_code
	drop construction_wage_rate_requireme-dod_claimant_program_description
	drop recovered_materials_sustainabili-place_of_manufacture
	drop recipient_legal_organization_nam-sba_certified_8a_joint_venture
	drop recipient_address_line_2-recipient_address_line_3 recipient_state_code recipient_county_name recipient_country_code recipient_phone_number
	drop recipient_fax_number-vendor_site_code_alt immediate_parent_uei-domestic_parent_uei_name ccr_registration_date-ik primary_place_of_performance_sta iq
	drop extent_competed_code primary_place_of_performance_con competitive_procedures_code-type_of_set_aside_code
	drop evaluated_preference_code-ji commercial_item_acquisition_proc-commercial_item_acquisition_proc
	drop jl-transaction_key
	
	replace awardeename = "Winnebago Tribe of Nebraska" if awardeename == "Winnebago Tribe Of Nebraska (9962)" | awardeename == "Winnebago Tribe Of Nebraska" | awardeename == "Little Priest Tribal College"	
	
	gen tribe_recipient = 0
	replace tribe_recipient = 1 if awardeename == "Winnebago Tribe of Nebraska"
	
	label var tribe_recipient "Tribe was direct recipient of awards not HCI"
	
	// SUPERECTOR 
	// there are some NAICS that are less than 6 digits, making null
	replace naics = "" if length(naics) < 6
	
	// two digit naics = sector
	gen sector = substr(naics,1,2)
	
	// creating supersector categories 
	// from bls https://www.bls.gov/sae/additional-resources/naics-supersectors-for-ces-program.htm
	
	gen supersector = ""
	replace supersector = "Natural Resources & Mining" if sector == "21"
	replace supersector = "Construction" if sector == "23"
	replace supersector = "Manufacturing" if sector == "31" | sector == "32" |sector == "33"
	replace supersector = "Trade, Transportation, & Utilities" if sector == "42" | sector == "44" |sector == "45" | sector == "48" |sector == "49" |sector == "22"
	replace supersector = "Information" if sector == "51"  
	replace supersector = "Financial Activities" if sector == "52" | sector == "53" 
	replace supersector = "Professional & Business Services" if sector == "54" | sector == "55" |sector == "56" 
	replace supersector = "Education & Health Services" if sector == "61" | sector == "62" 
	replace supersector = "Leisure & Hospitality" if sector == "71" | sector == "72" 
	replace supersector = "Other services or Not given" if sector == "." | sector == "81" | sector == "91" | sector == "92" | sector == "93" | sector == ""
	
	// create better organized set-aside categories
	replace setasidehighergov = itrim(setasidehighergov) // remove any potential empty space at end of awardee name
	replace setasidehighergov = trim(setasidehighergov)  // remove any potential empty space at other end of awardee name
	
	gen setaside = ""
	replace setaside = "8(a)" if setasidehighergov == "8(A) Competed (8A)" | setasidehighergov == "8(A) Sole Source (8AN)" | setasidehighergov == "8(A) With Hub Zone Preference (HS3)" 
	replace setaside = "Buy Indian" if setasidehighergov == "Buy Indian (BI)"
	replace setaside = "Other" if setasidehighergov == "HBCU Or MI Set-Aside -- Total (HMT)" 
	replace setaside = "Indian Business"  if setasidehighergov == "Indian Economic Enterprise (IEE)" | setasidehighergov == "Indian Small Business Economic Enterprise (ISBEE)"
	replace setaside = "HUBZone"  if setasidehighergov == "Hubzone Set-Aside (HZC)" | setasidehighergov == "Hubzone Sole Source  (HZS)"
	replace setaside = "Small Business" if setasidehighergov == "Small Business Set Aside - Total (SBA)" | setasidehighergov == "Reserved For Small Business (RSB)"
	replace setaside = "No set-aside used" if typeofsetaside == "NO SET ASIDE USED."
	replace setaside = "None reported" if setasidehighergov == ""
	
	gen defense = 0
	replace defense = 1 if funding_agency == "Dept Of Defense"
	
	label var defense "Defense contract or DoD is top level funding agency"
	
	sort year 
	
	drop if year == 2023
	
	gen inflyear = year 
	merge m:1 inflyear using annualinflation , keep(3) nogen
	
	gen i_transaction_value = inflfac*transaction_value
	label var i_transaction_value "value of transaction in 2022 dollars"
	
	gen i_total_dollars_obligated = inflfac*total_dollars_obligated
	label var i_total_dollars_obligated "Total value of contract in 2022 dollars"
	
	label var sector "2 digit NAICS code"
	label var supersector "BLS Supersectors"
	label var setaside "consolidated set-aside categories"
	
	rename uei_id awardee_uei
	
	save "~/Dropbox/Winnebago/ESM/clean/prime file.dta", replace
	
} // rawfpds

if $rawfsrs==1{
	
	import excel "~/Dropbox/Winnebago/ESM/raw/Data Request 3-19.xlsx", sheet("Sub Awards") firstrow case(lower) clear
	
	rename subawardactiondatefiscalyear year
	
	rename subawardamounttotal sub_transaction_value
	
	drop if year == 2023
	
	replace subawardeename = "All Native Solutions Corporation" if subawardeename == "Allnative Solutions Corporation"
	replace subawardeename = "All Native Systems LLC" if subawardeename == "All Native Systems Llc"
	replace subawardeename = "All Native Systems LLC" if subawardeename == "All Native Systems, L.L.C."
	replace subawardeename = "All Native, Inc." if subawardeename == "All Native"
	replace subawardeename = "Blue Earth Marketing Company" if subawardeename == "Blue Earth Marketing"
	replace subawardeename = "Dynamic Systems, Inc" if subawardeename == "Dynamic Systems, Inc." 
	replace subawardeename = "HCI Management Services Company" if subawardeename == "Hci Management Services Company" 
	replace subawardeename = "HCI Logistics Company" if subawardeename == "Hci Logistics Company" 
	replace subawardeename = "HCI Distribution Company" if subawardeename == "Hci Distribution Company" 
	replace subawardeename = "HCI Construction" if subawardeename == "Hci Construction Company" | subawardeename == "Hci Construction" | subawardeename == "H C I Construction" 
	replace subawardeename = "Protege Health Services LLC" if subawardeename == "Protege Health Services Llc" | subawardeename == "Protege Health Services, Llc"
	replace subawardeename = "Wincomp LLC" if subawardeename == "Wincomp L L C Dba All Native"
	replace subawardeename = "Wincomp LLC" if subawardeename == "Wincomp Llc"
	replace subawardeename = "Wincomp LLC" if subawardeename == "Wincomp Limited Liability Company"
	
	gen inflyear = year 
	merge m:1 inflyear using annualinflation , keep(3) nogen
	
	gen i_sub_transaction_value = inflfac*sub_transaction_value
	label var i_sub_transaction_value "value of sub transaction in 2022 dollars"
	
	rename subawardeeuei awardee_uei
	
	gen tribe_recipient = 0
	replace tribe_recipient = 1 if subawardeename == "Winnebago Tribe of Nebraska"
	
	label var tribe_recipient "Tribe was direct recipient of awards not HCI"
	
	save "~/Dropbox/Winnebago/ESM/clean/sub file.dta", replace
	
} // rawfsrs

if $primetrends==1{
	
	use "~/Dropbox/Winnebago/ESM/clean/prime file.dta", clear
	
	drop if tribe_recipient == 1 // to isolate HCI only
	
	collapse (sum) transaction_value, by(year)
	
	// PRIME
	
	#delimit;
	
	twoway bar transaction_value year,
	
	title( 
			"Figure [E001]: HCI Prime Award Obligations", size(medium))
			subtitle("2001-2022", size(small))
			note("Source: FPDS-NG accessed via HigherGov" ///
			"Note: 2001 is the first year we observe federal obligations to HCI and its subsidiaries." ///
			"We do observe federal obligations in 1999 where the Winnebago Tribe of Nebraska was the awardee." ///
			"HigherGov observes that federal contracting data becomes less reliable prior to 2000." ///
			"Preliminary Draft - Subject to Revision")
			xlabel(2001 "2001" 2008 "2008" 2015 "2015" 2022 "2022")
			ylabel(0 "$0" 100000000 "$100M" 200000000 "$200M" 300000000 "$300M")
			xsize(11) ysize(8)
			ytitle("nominal dollars")
			xtitle("year")
	
	;
	#delimit cr
	
	graph export "~/Dropbox/Winnebago/ESM/results/[E001]primetrends.pdf", replace
	
} // primetrends

if $subtrends==1{
	
	use "~/Dropbox/Winnebago/ESM/clean/sub file.dta", clear
	
	drop if tribe_recipient == 1 // to isolate HCI only
	
	// SUBCONTRACTING 
	
	collapse (sum) sub_transaction_value, by(year)
	
	#delimit;
	
	twoway bar sub_transaction_value year,
	
	title( 
			"Figure [E002]: HCI Sub Award Obligations", size(medium))
			subtitle("2013-2022", size(small))
			note("Source: FSRS accessed via HigherGov" ///
			"Note: Sub Award obligations data availability begins in 2010 due to the implementation schedule of the Federal Funding Accountability and Transparency Act (FFATA)." ///
			"This means that we cannot reliably capture Sub Award Obligations prior to 2010 even though they may exist." ///
			"Preliminary Draft - Subject to Revision")
			ylabel(0 "$0" 5000000 "$5M" 10000000 "$10M" 15000000 "$15M")
			xsize(11) ysize(8)
			ytitle("nominal dollars")
			xtitle("year")
			xlabel(2013(3)2022)
	
	;
	#delimit cr
	
	graph export "~/Dropbox/Winnebago/ESM/results/[E002]subtrends.pdf", replace
	
} // subtrends

if $idvtrends==1{
	
	use "~/Dropbox/Winnebago/ESM/clean/idv file.dta", clear
	
	drop if tribe_recipient == 1 // to isolate HCI only
	
	// IDV 
	
	collapse (sum) idv_transaction_value, by(year)
	
	#delimit;
	
	twoway bar idv_transaction_value year,
	
	title( 
			"Figure [E003]: HCI IDV Award Obligations", size(medium))
			subtitle("2006-2022", size(small))
			note("Source: FPDS-NG accessed via HigherGov" ///
			"Preliminary Draft - Subject to Revision")
			ylabel(0 "$0" 20000000 "$20M" 40000000 "$40M" 60000000 "$60M" )
			xsize(11) ysize(8)
			ytitle("nominal dollars")
			xtitle("year")
			xlabel(2006(4)2022)
	
	;
	#delimit cr
	
	graph export "~/Dropbox/Winnebago/ESM/results/[E003]idvtrends.pdf", replace
	
	
} // idvtrends

if $totaltrends==1{
	
	// PRIME
	use "~/Dropbox/Winnebago/ESM/clean/prime file.dta", clear
	
	drop if tribe_recipient == 1 // to isolate HCI only
	
	collapse (sum) transaction_value, by(year)
	
	save "~/Dropbox/Winnebago/ESM/intermediate/prime.dta", replace
	
	// SUB
	use "~/Dropbox/Winnebago/ESM/clean/sub file.dta", clear
	
	collapse (sum) sub_transaction_value, by(year)
	
	save "~/Dropbox/Winnebago/ESM/intermediate/sub.dta", replace
	
	// IDV
	use "~/Dropbox/Winnebago/ESM/clean/idv file.dta", clear
	
	collapse (sum) idv_transaction_value, by(year)
	
	save "~/Dropbox/Winnebago/ESM/intermediate/idv.dta", replace
	
	// COMBINE
	
	use "~/Dropbox/Winnebago/ESM/intermediate/prime.dta", clear
	
	merge 1:1 year using  "~/Dropbox/Winnebago/ESM/intermediate/sub.dta"
	
	drop _merge
	
	merge 1:1 year using  "~/Dropbox/Winnebago/ESM/intermediate/idv.dta"
	
	drop _merge
	
	#delimit;
	
	graph bar transaction_value sub_transaction_value idv_transaction_value, over(year, lab(ang(v))) stack legend(order(1 "Prime Award Obligations" 2
"Sub Award Obligations" 3 "IDV Award Obligations"))
	
	title( 
			"Figure [E004]: HCI Total Award Obligations", size(medium))
			subtitle("2001-2022", size(small))
			note("Source: FPDS & FSRS accessed via HigherGov & FRED" ///
			"Note: Sub Award obligations data availability begins in 2010 due to the implementation schedule of the Federal Funding Accountability and Transparency Act (FFATA)." ///
			"This means that we cannot reliably capture Sub Award Obligations prior to 2010 even though they may exist." ///
			"Preliminary Draft - Subject to Revision")
			ylabel(0 "$0" 100000000 "$100M" 200000000 "$200M" 300000000 "$300M")
			xsize(11) ysize(8)
			ytitle("nominal dollars")
	
	;
	#delimit cr
	
	graph export "~/Dropbox/Winnebago/ESM/results/[E004]totaltrends.pdf", replace
	
	
} // totaltrends

if $subsidiarydollars==1{
	
	use "~/Dropbox/Winnebago/ESM/clean/prime file.dta", clear
	
	drop if tribe_recipient == 1 // to isolate HCI only
	
	collapse (sum) transaction_value, by(awardeename)
	
	#delimit;
	
	graph hbar transaction_value, over(awardeename, sort(1) descending)
	
	title( 
			"Figure [E005]: HCI & Subsidiaries Prime Obligations", size(medium))
			subtitle("2001-2022", size(small))
			note("Source: FPDS-NG accessed via HigherGov" ///
			"Note: All companies listed were reported as unique awardee's for contracts" ///
			"Preliminary Draft - Subject to Revision")
			ylabel(0 "$0" 300000000 "$300M" 600000000 "$600M")
			xsize(8) ysize(11)
			ytitle("nominal dollars")
	
	;
	#delimit cr
	
	graph export "~/Dropbox/Winnebago/ESM/results/[E005]subsidiary.pdf", replace
	 
} // subsidiarydollars

if $setaside==1{
	
	use "~/Dropbox/Winnebago/ESM/clean/prime file.dta", clear
	
	drop if tribe_recipient == 1 // to isolate HCI only
	
	collapse (sum) transaction_value, by(setaside)
	
	egen total_obligations = total(transaction_value)
	
	gen share_setaside = transaction_value/total_obligations
	
	#delimit;
	
	graph hbar share_setaside, over(setaside, sort(1) descending)
	
	title( 
			"Figure [E006]: HCI Share of Prime Obligations by Set-Aside", size(medium))
			subtitle("2001-2022", size(small))
			note("Source: FPDS-NG accessed via HigherGov" ///
			"Preliminary Draft - Subject to Revision")
			ylabel(0 "0%" .2 "20%" .4 "40%" .6 "60%" .8 "80%" )
			xsize(11) ysize(8)
			ytitle("share of prime award obligations")
			
	
	;
	#delimit cr
	
	graph export "~/Dropbox/Winnebago/ESM/results/[E006]setaside.pdf", replace
	
} // setaside

if $growthsetaside==1{
	
	use "~/Dropbox/Winnebago/ESM/clean/prime file.dta", clear
	
	drop if tribe_recipient == 1 // to isolate HCI only
	
	collapse (sum) transaction_value, by(year setaside)
	
	// coded to add scatter plot labels
	gen one = "8(a)" if setaside == "8(a)"
	gen two = "Indian Business" if setaside == "Indian Business"
	gen three = "HUBZone" if setaside == "HUBZone" 
	
	#delimit;
	
	graph twoway line  transaction_value year if setaside == "8(a)", sort lwidth(medthick) lc("$blue3") ||
	             line  transaction_value year if setaside == "HUBZone", sort lwidth(medthick) lc("$red3") ||
				 line  transaction_value year if setaside == "Indian Business", sort lwidth(medthick) lc("$green3") ||
				 scatter transaction_value year if year == 2022, mlabel(one) msymbol(none) mlabposition(3) mlabsize(small) mlabcolor("$blue3") ||
				 scatter transaction_value year if year == 2022, mlabel(three) msymbol(none) mlabposition(2) mlabsize(small) mlabcolor("$red3") ||
				 scatter transaction_value year if year == 2022, mlabel(two) msymbol(none) mlabposition(11) mlabsize(small) mlabcolor("$green3") 
		 
	
	title( 
			"Figure [E007]: HCI Key Set-Aside Trends for Prime Award Obligations", size(medium))
			subtitle("2001-2022", size(small))
			note("Source: FPDS-NG accessed via HigherGov & FRED" ///
			"Preliminary Draft - Subject to Revision")
			xlabel(2001(7)2024)
			ylabel(0 "$0" 50000000 "$50M" 100000000 "$100M" 150000000 "$150M" 200000000 "$200M" 250000000 "$250M")
			xsize(11) ysize(8)
			ytitle("nominal dollars")
			xtitle("year")
			legend(off)
	
	;
	#delimit cr
	
	graph export "~/Dropbox/Winnebago/ESM/results/[E007]setasidetrends.pdf", replace
	
} // growthsetaside

if $supersector==1{
	
	use "~/Dropbox/Winnebago/ESM/clean/prime file.dta", clear
	
	drop if tribe_recipient == 1 // to isolate HCI only
	
	collapse (sum) transaction_value, by(defense supersector)
	
	egen total_obligations = total(transaction_value), by(defense)
	
	gen share_supersector = transaction_value/total_obligations
	
	// civilian has one less category than defense because no obligations were generated so I am adding so that graphs match
	
	set obs `=_N+1'
	
	replace supersector = "Natural Resources & Mining" if defense == .
	replace defense = 0 if defense == .
	replace transaction_value = 0 if transaction_value == .
	replace share_supersector = 0 if share_supersector == .
	replace total_obligations = 0 if total_obligations == .
	
	// defense has one less category 
	
	set obs `=_N+1'
	
	replace supersector = "Leisure & Hospitality" if defense == .
	replace defense = 1 if defense == .
	replace transaction_value = 0 if transaction_value == .
	replace share_supersector = 0 if share_supersector == .
	replace total_obligations = 0 if total_obligations == .
	
	sort defense supersector
	
	// civilian
	#delimit;
	
	graph hbar share_supersector if defense ==0, over(supersector) bar(1,
color("$blue4"))
	
			subtitle("Civilian Contracts", size(medium))
	
			ylabel(0 "0%" .25 "25%" .5 "50%" .75 "75%" )
			xsize(11) ysize(8)
			ytitle("share of prime award obligations by supersector")
			
		
	;
	#delimit cr
	graph save civilian.gph, replace
	
	// defense
	#delimit;
	
	graph hbar share_supersector if defense ==1, over(supersector) bar(1,
color("$red4"))
	
			subtitle("Defense Contracts", size(medium))
	
			ylabel(0 "0%" .25 "25%" .5 "50%" .75 "75%")
			xsize(11) ysize(8)
			ytitle("share of prime award obligations by supersector")
			
		
	;
	#delimit cr
	graph save defense.gph, replace
	
	#delimit;
	
	graph combine civilian.gph defense.gph, iscale(*.9)
	
	title( 
			"Figure [E008]: HCI Share of Prime Award Obligations by Supersector", size(medium))
			subtitle("2001-2022", size(small))
			note("Source: FPDS-NG accessed via HigherGov & BLS" ///
			"Note: Other services or Not given combines all other remaining sector codes and contracts where a sector wasn't reported" ///
			"Civilian contracting accounts for 69% of overall Prime Award Obligations while defense contracting accounts for 31% in 2001-2022" ///
			"Preliminary Draft - Subject to Revision")
			xsize(11) ysize(8)
	
	;
	#delimit cr
	
	graph export "~/Dropbox/Winnebago/ESM/results/[E008]supersector.pdf", replace
	
} // supersector

if $supersectortrends==1{
	
	use "~/Dropbox/Winnebago/ESM/clean/prime file.dta", clear
	
	drop if tribe_recipient == 1 // to isolate HCI only
	
	collapse (sum) transaction_value, by(year supersector)
	
	// coded to add scatter plot labels
	gen one = "Financial Activities" if supersector == "Financial Activities"
	gen two = "Information" if supersector == "Information"
	gen three = "Manufacturing" if supersector == "Manufacturing" 
	gen four = "Construction" if supersector == "Construction"
	gen five = "Professional & Business Services" if supersector == "Professional & Business Services" 
	
	#delimit;
	
	graph twoway line  transaction_value year if supersector == "Financial Activities", sort lwidth(medthick) lc("$blue3") ||
			     line  transaction_value year if supersector == "Information", sort lwidth(medthick) lc("$gray4") ||
				 line  transaction_value year if supersector == "Manufacturing", sort lwidth(medthick) lc("$red3") ||
	             line  transaction_value year if supersector == "Construction", sort lwidth(medthick) lc("$gold3") ||
				 line  transaction_value year if supersector == "Professional & Business Services", sort lwidth(medthick) lc("$green3") ||
				 scatter transaction_value year if year == 2022, mlabel(one) msymbol(none) mlabposition(2) mlabsize(small) mlabcolor("$blue3") ||
				 scatter transaction_value year if year == 2022, mlabel(two) msymbol(none) mlabposition(2) mlabsize(small) mlabcolor("$gray4") ||
				 scatter transaction_value year if year == 2022, mlabel(three) msymbol(none) mlabposition(2) mlabsize(small) mlabcolor("$red3") ||
				 scatter transaction_value year if year == 2022, mlabel(four) msymbol(none) mlabposition(2) mlabsize(small) mlabcolor("$gold3") ||
				 scatter transaction_value year if year == 2021, mlabel(five) msymbol(none) mlabposition(12) mlabsize(small) mlabcolor("$green3") 
		 
	
	title( 
			"Figure [E009]: HCI Top Five Supersector Trends", size(medium))
			subtitle("2001-2022", size(small))
			note("Source: FPDS-NG accessed via HigherGov & FRED & BLS" ///
			"Preliminary Draft - Subject to Revision")
			xlabel(2001(7)2026)
			ylabel(0 "$0" 50000000 "$50M" 100000000 "$100M" 150000000 "$150M" 200000000 "$200M")
			xsize(11) ysize(8)
			ytitle("nominal dollars")
			xtitle("year")
			legend(off)
	
	;
	#delimit cr
	
	graph export "~/Dropbox/Winnebago/ESM/results/[E009]supersectortrends.pdf", replace
	
	
} // supersectortrends

if $totaltrends2022==1{
	
	// PRIME
	use "~/Dropbox/Winnebago/ESM/clean/prime file.dta", clear
	
	drop if tribe_recipient == 1 // to isolate HCI only
	
	collapse (sum) transaction_value, by(year)
	
	save "~/Dropbox/Winnebago/ESM/intermediate/prime.dta", replace
	
	// SUB
	use "~/Dropbox/Winnebago/ESM/clean/sub file.dta", clear
	
	drop if tribe_recipient == 1 // to isolate HCI only
	
	collapse (sum) sub_transaction_value, by(year)
	
	save "~/Dropbox/Winnebago/ESM/intermediate/sub.dta", replace
	
	// IDV
	use "~/Dropbox/Winnebago/ESM/clean/idv file.dta", clear
	
	drop if tribe_recipient == 1 // to isolate HCI only
	
	collapse (sum) idv_transaction_value, by(year)
	
	save "~/Dropbox/Winnebago/ESM/intermediate/idv.dta", replace
	
	// COMBINE
	
	use "~/Dropbox/Winnebago/ESM/intermediate/prime.dta", clear
	
	merge 1:1 year using  "~/Dropbox/Winnebago/ESM/intermediate/sub.dta"
	
	drop _merge
	
	merge 1:1 year using  "~/Dropbox/Winnebago/ESM/intermediate/idv.dta"
	
	drop _merge
	
	keep if year == 2022
	
	#delimit;
	
	graph bar transaction_value sub_transaction_value idv_transaction_value, over(year) stack legend(order(1 "Prime Award Obligations" 2
"Sub Award Obligations" 3 "IDV Award Obligations"))
	
	title( 
			"Figure [E010]: HCI Total Award Obligations", size(medium))
			subtitle("2022", size(small))
			note("Source: FPDS & FSRS accessed via HigherGov & FRED" ///
			"Note: Sub Award obligations data availability begins in 2010 due to the implementation schedule of the Federal Funding Accountability and Transparency Act (FFATA)." ///
			"This means that we cannot reliably capture Sub Award Obligations prior to 2010 even though they may exist." ///
			"Preliminary Draft - Subject to Revision")
			ylabel(0 "$0" 100000000 "$100M" 200000000 "$200M" 300000000 "$300M")
			xsize(11) ysize(8)
			ytitle("nominal dollars")
	
	;
	#delimit cr
	
	graph export "~/Dropbox/Winnebago/ESM/results/[E010]totaltrends2022.pdf", replace
	
	
} // totaltrends2022

if $subsidiarydollars2022==1{
	
	use "~/Dropbox/Winnebago/ESM/clean/prime file.dta", clear
	
	drop if tribe_recipient == 1 // to isolate HCI only
	
	keep if year == 2022
	
	collapse (sum) transaction_value, by(awardeename)
	
	#delimit;
	
	graph hbar transaction_value, over(awardeename, sort(1) descending)
	
	title( 
			"Figure [E011]: HCI & Subsidiaries Prime Obligations", size(medium))
			subtitle("2022", size(small))
			note("Source: FPDS-NG accessed via HigherGov" ///
			"Note: All companies listed were reported as unique awardee's for contracts" ///
			"Preliminary Draft - Subject to Revision")
			ylabel(0 "$0" 60000000 "$60M" 120000000 "$120M")
			xsize(8) ysize(11)
			ytitle("nominal dollars")
	
	;
	#delimit cr
	
	graph export "~/Dropbox/Winnebago/ESM/results/[E011]subsidiary2022.pdf", replace
	 
} // subsidiarydollars2022

if $setaside2022==1{
	
	use "~/Dropbox/Winnebago/ESM/clean/prime file.dta", clear
	
	drop if tribe_recipient == 1 // to isolate HCI only
	
	keep if year == 2022 
	
	collapse (sum) transaction_value, by(setaside)
	
	egen total_obligations = total(transaction_value)
	
	gen share_setaside = transaction_value/total_obligations
	
	#delimit;
	
	graph hbar share_setaside, over(setaside, sort(1) descending)
	
	title( 
			"Figure [E012]: HCI Share of Prime Obligations by Set-Aside", size(medium))
			subtitle("2022", size(small))
			note("Source: FPDS-NG accessed via HigherGov" ///
			"Preliminary Draft - Subject to Revision")
			ylabel(0 "0%" .2 "20%" .4 "40%" .6 "60%" .8 "80%" )
			xsize(11) ysize(8)
			ytitle("share of prime award obligations")
			
	
	;
	#delimit cr
	
	graph export "~/Dropbox/Winnebago/ESM/results/[E012]setaside2022.pdf", replace
	
} // setaside2022

if $supersector2022==1{
	
	use "~/Dropbox/Winnebago/ESM/clean/prime file.dta", clear
	
	drop if tribe_recipient == 1 // to isolate HCI only
	
	keep if year == 2022
	
	collapse (sum) transaction_value, by(defense supersector)
	
	egen total_obligations = total(transaction_value), by(defense)
	
	gen share_supersector = transaction_value/total_obligations
	
	// civilian has one less category than defense because no obligations were generated so I am adding so that graphs match
	
	set obs `=_N+1'
	
	replace supersector = "Natural Resources & Mining" if defense == .
	replace defense = 0 if defense == .
	replace transaction_value = 0 if transaction_value == .
	replace share_supersector = 0 if share_supersector == .
	replace total_obligations = 0 if total_obligations == .
	
	// defense has one less category 
	
	set obs `=_N+1'
	
	replace supersector = "Leisure & Hospitality" if defense == .
	replace defense = 1 if defense == .
	replace transaction_value = 0 if transaction_value == .
	replace share_supersector = 0 if share_supersector == .
	replace total_obligations = 0 if total_obligations == .
	
	// civilian has one less category than defense because no obligations were generated so I am adding so that graphs match
	
	set obs `=_N+1'
	
	replace supersector = "Financial Activities" if defense == .
	replace defense = 0 if defense == .
	replace transaction_value = 0 if transaction_value == .
	replace share_supersector = 0 if share_supersector == .
	replace total_obligations = 0 if total_obligations == .
	
	// civilian has one less category than defense because no obligations were generated so I am adding so that graphs match
	
	set obs `=_N+1'
	
	replace supersector = "Leisure & Hospitality" if defense == .
	replace defense = 0 if defense == .
	replace transaction_value = 0 if transaction_value == .
	replace share_supersector = 0 if share_supersector == .
	replace total_obligations = 0 if total_obligations == .
	
	// defense has one less category 
	
	set obs `=_N+1'
	
	replace supersector = "Natural Resources & Mining" if defense == .
	replace defense = 1 if defense == .
	replace transaction_value = 0 if transaction_value == .
	replace share_supersector = 0 if share_supersector == .
	replace total_obligations = 0 if total_obligations == .
	
	sort defense supersector
	
	// civilian
	#delimit;
	
	graph hbar share_supersector if defense ==0, over(supersector) bar(1,
color("$blue4"))
	
			subtitle("Civilian Contracts", size(medium))
	
			ylabel(0 "0%" .25 "25%" .5 "50%" .75 "75%" )
			xsize(11) ysize(8)
			ytitle("share of prime obligations by supersector")
			
		
	;
	#delimit cr
	graph save civilian.gph, replace
	
	// defense
	#delimit;
	
	graph hbar share_supersector if defense ==1, over(supersector) bar(1,
color("$red4"))
	
			subtitle("Defense Contracts", size(medium))
	
			ylabel(0 "0%" .25 "25%" .5 "50%" .75 "75%")
			xsize(11) ysize(8)
			ytitle("share of prime obligations by supersector")
			
		
	;
	#delimit cr
	graph save defense.gph, replace
	
	#delimit;
	
	graph combine civilian.gph defense.gph, iscale(*.9)
	
	title( 
			"Figure [E013]: HCI Share of Prime Award Obligations by Supersector", size(medium))
			subtitle("2022", size(small))
			note("Source: FPDS-NG accessed via HigherGov & BLS" ///
			"Note: Other services or Not given combines all other remaining sector codes and contracts where a sector wasn't reported" ///
			"Civilian contracting accounts for 82% of overall Prime Award Obligations while defense contracting accounts for 18% in 2022" ///
			"Preliminary Draft - Subject to Revision")
			xsize(11) ysize(8)
	
	;
	#delimit cr
	
	graph export "~/Dropbox/Winnebago/ESM/results/[E013]supersector2022.pdf", replace
	
} // supersector2022

if $awardandcompact==1{
	
	// HCI only
	// PRIME
	use "~/Dropbox/Winnebago/ESM/clean/prime file.dta", clear
	
	drop if tribe_recipient == 1
	collapse (sum) transaction_value, by(year)
	
	rename transaction_value transaction_value_hci
	
	save "~/Dropbox/Winnebago/ESM/intermediate/prime hci.dta", replace
	
	// SUB
	use "~/Dropbox/Winnebago/ESM/clean/sub file.dta", clear
	
	drop if tribe_recipient == 1
	collapse (sum) sub_transaction_value, by(year)
	
	rename sub_transaction_value sub_transaction_value_hci
	
	save "~/Dropbox/Winnebago/ESM/intermediate/sub hci.dta", replace
	
	// IDV
	use "~/Dropbox/Winnebago/ESM/clean/idv file.dta", clear
	
	drop if tribe_recipient == 1
	collapse (sum) idv_transaction_value, by(year)
	
	rename idv_transaction_value idv_transaction_value_hci
	
	save "~/Dropbox/Winnebago/ESM/intermediate/idv hci.dta", replace
	
	// Winnebago Tribe only
	// PRIME
	use "~/Dropbox/Winnebago/ESM/clean/prime file.dta", clear
	
	keep if tribe_recipient == 1
	collapse (sum) transaction_value, by(year)
	
	save "~/Dropbox/Winnebago/ESM/intermediate/prime.dta", replace
	
	// IDV
	use "~/Dropbox/Winnebago/ESM/clean/idv file.dta", clear
	
	keep if tribe_recipient == 1
	collapse (sum) idv_transaction_value, by(year)
	
	save "~/Dropbox/Winnebago/ESM/intermediate/idv.dta", replace
	
	// IHS
	use "~/Dropbox/Winnebago/ESM/clean/ihs file.dta", clear
	
	keep if tribe_recipient == 1
	collapse (sum) ihs638_transaction_value, by(year)
	
	save "~/Dropbox/Winnebago/ESM/intermediate/ihs.dta", replace
	
	// COMBINE
	
	use "~/Dropbox/Winnebago/ESM/intermediate/prime.dta", clear
	
	merge 1:1 year using  "~/Dropbox/Winnebago/ESM/intermediate/idv.dta"
	
	drop _merge
	
	merge 1:1 year using  "~/Dropbox/Winnebago/ESM/intermediate/ihs.dta"
	
	drop _merge
	
	merge 1:1 year using  "~/Dropbox/Winnebago/ESM/intermediate/sub hci.dta"
	
	drop _merge
	
	merge 1:1 year using  "~/Dropbox/Winnebago/ESM/intermediate/idv hci.dta"
	
	drop _merge
	
	merge 1:1 year using  "~/Dropbox/Winnebago/ESM/intermediate/prime hci.dta"
	
	drop _merge
	
	// coding missing as zero so it sums. But missing means did not find data 
	replace sub_transaction_value = 0 if sub_transaction_value == .
	replace idv_transaction_value = 0 if idv_transaction_value == .
	replace ihs638_transaction_value = 0 if ihs638_transaction_value == .
	replace transaction_value = 0 if transaction_value == .
	replace idv_transaction_value_hci = 0 if idv_transaction_value_hci == .
	replace sub_transaction_value_hci = 0 if sub_transaction_value_hci == .
	replace transaction_value_hci = 0 if transaction_value_hci == .
		
	gen total_transactions_tribe = transaction_value + idv_transaction_value
	
	gen total_transactions_hci = transaction_value_hci + sub_transaction_value_hci + idv_transaction_value_hci
	
	#delimit;
	
	graph bar total_transactions_hci total_transactions_tribe  ihs638_transaction_value, over(year , lab(ang(v))) stack legend(order(1 "HCI Award Obligations" 2 "Winnebago Tribe Award Obligations" 3 "IHS 638 Direct Payments"))
	
	title( 
			"Figure [E014]: HCI & Winnebago Tribe Total Award Obligations & IHS 638 Payments", size(medium))
			subtitle("1999-2022", size(small))
			note("Source: FPDS & FSRS accessed via HigherGov & FRED" ///
			"Note: Sub Award obligations data availability begins in 2010 due to the implementation schedule of the Federal Funding Accountability and Transparency Act (FFATA)." ///
			"This means that we cannot reliably capture Sub Award Obligations prior to 2010 even though they may exist." ///
			"This combines all award obligations - Prime, Sub and IDV Awards for HCI and Winnebago Tribe of Nebraska seperately." ///
			"This additionally includes IHS 638 direct payments to the Tribe as its own category" ///
			"Preliminary Draft - Subject to Revision")
			ylabel(0 "$0" 100000000 "$100M" 200000000 "$200M" 300000000 "$300M" 400000000 "$400M")
			xsize(11) ysize(8)
			ytitle("nominal dollars")
	
	;
	#delimit cr
	
	graph export "~/Dropbox/Winnebago/ESM/results/[E014]awardandcompact.pdf", replace
	
	
} // awardandcompact

if $awardandcompact2022==1{
	
	// HCI only
	// PRIME
	use "~/Dropbox/Winnebago/ESM/clean/prime file.dta", clear
	
	drop if tribe_recipient == 1
	collapse (sum) transaction_value, by(year)
	
	rename transaction_value transaction_value_hci
	
	save "~/Dropbox/Winnebago/ESM/intermediate/prime hci.dta", replace
	
	// SUB
	use "~/Dropbox/Winnebago/ESM/clean/sub file.dta", clear
	
	drop if tribe_recipient == 1
	collapse (sum) sub_transaction_value, by(year)
	
	rename sub_transaction_value sub_transaction_value_hci
	
	save "~/Dropbox/Winnebago/ESM/intermediate/sub hci.dta", replace
	
	// IDV
	use "~/Dropbox/Winnebago/ESM/clean/idv file.dta", clear
	
	drop if tribe_recipient == 1
	collapse (sum) idv_transaction_value, by(year)
	
	rename idv_transaction_value idv_transaction_value_hci
	
	save "~/Dropbox/Winnebago/ESM/intermediate/idv hci.dta", replace
	
	// Winnebago Tribe only
	// PRIME
	use "~/Dropbox/Winnebago/ESM/clean/prime file.dta", clear
	
	keep if tribe_recipient == 1
	collapse (sum) transaction_value, by(year)
	
	save "~/Dropbox/Winnebago/ESM/intermediate/prime.dta", replace
	
	// IDV
	use "~/Dropbox/Winnebago/ESM/clean/idv file.dta", clear
	
	keep if tribe_recipient == 1
	collapse (sum) idv_transaction_value, by(year)
	
	save "~/Dropbox/Winnebago/ESM/intermediate/idv.dta", replace
	
	// IHS
	use "~/Dropbox/Winnebago/ESM/clean/ihs file.dta", clear
	
	keep if tribe_recipient == 1
	collapse (sum) ihs638_transaction_value, by(year)
	
	save "~/Dropbox/Winnebago/ESM/intermediate/ihs.dta", replace
	
	// COMBINE
	
	use "~/Dropbox/Winnebago/ESM/intermediate/prime.dta", clear
	
	merge 1:1 year using  "~/Dropbox/Winnebago/ESM/intermediate/idv.dta"
	
	drop _merge
	
	merge 1:1 year using  "~/Dropbox/Winnebago/ESM/intermediate/ihs.dta"
	
	drop _merge
	
	merge 1:1 year using  "~/Dropbox/Winnebago/ESM/intermediate/sub hci.dta"
	
	drop _merge
	
	merge 1:1 year using  "~/Dropbox/Winnebago/ESM/intermediate/idv hci.dta"
	
	drop _merge
	
	merge 1:1 year using  "~/Dropbox/Winnebago/ESM/intermediate/prime hci.dta"
	
	drop _merge
	
	// coding missing as zero so it sums. But missing means did not find data 
	replace sub_transaction_value = 0 if sub_transaction_value == .
	replace idv_transaction_value = 0 if idv_transaction_value == .
	replace ihs638_transaction_value = 0 if ihs638_transaction_value == .
	replace transaction_value = 0 if transaction_value == .
	replace idv_transaction_value_hci = 0 if idv_transaction_value_hci == .
	replace sub_transaction_value_hci = 0 if sub_transaction_value_hci == .
	replace transaction_value_hci = 0 if transaction_value_hci == .
		
	keep if year == 2022 
	
	gen total_transactions_tribe = transaction_value + idv_transaction_value
	
	gen total_transactions_hci = transaction_value_hci + sub_transaction_value_hci + idv_transaction_value_hci
	
	#delimit;
	
	graph bar total_transactions_hci  ihs638_transaction_value, over(year) stack legend(order(1 "HCI Award Obligations" 2 "IHS 638 Direct Payments"))
	
	title( 
			"Figure [E015]: Winnebago Tribe & HCI Total Award Obligations & IHS 638 Payments", size(medium))
			subtitle("2022", size(small))
			note("Source: FPDS & FSRS accessed via HigherGov & FRED" ///
			"Note: Sub Award obligations data availability begins in 2010 due to the implementation schedule of the Federal Funding Accountability and Transparency Act (FFATA)." ///
			"This means that we cannot reliably capture Sub Award Obligations prior to 2010 even though they may exist." ///
			"This combines all award obligations - Prime, Sub and IDV Awards for HCI and Winnebago Tribe of Nebraska seperately." ///
			"In 2022, the Winnebago Tribe of Nebraska was not a direct awardee of obligations which is why it is not shown." ///
			"This additionally includes IHS 638 direct payments to the Tribe as its own category" ///
			"Preliminary Draft - Subject to Revision")
			ylabel(0 "$0" 150000000 "$150M" 300000000 "$300M")
			xsize(11) ysize(8)
			ytitle("nominal dollars")
	
	;
	#delimit cr
	
	graph export "~/Dropbox/Winnebago/ESM/results/[E015]awardandcompact2022.pdf", replace
	
	
} // awardandcompact2022

if $awardandcompacttribe==1{
	
	// Winnebago Tribe only
	// PRIME
	use "~/Dropbox/Winnebago/ESM/clean/prime file.dta", clear
	
	keep if tribe_recipient == 1
	collapse (sum) transaction_value, by(year)
	
	save "~/Dropbox/Winnebago/ESM/intermediate/prime.dta", replace
	
	// IDV
	use "~/Dropbox/Winnebago/ESM/clean/idv file.dta", clear
	
	keep if tribe_recipient == 1
	collapse (sum) idv_transaction_value, by(year)
	
	save "~/Dropbox/Winnebago/ESM/intermediate/idv.dta", replace
	
	// IHS
	use "~/Dropbox/Winnebago/ESM/clean/ihs file.dta", clear
	
	keep if tribe_recipient == 1
	collapse (sum) ihs638_transaction_value, by(year)
	
	save "~/Dropbox/Winnebago/ESM/intermediate/ihs.dta", replace
	
	// COMBINE
	
	use "~/Dropbox/Winnebago/ESM/intermediate/prime.dta", clear
	
	merge 1:1 year using  "~/Dropbox/Winnebago/ESM/intermediate/idv.dta"
	
	drop _merge
	
	merge 1:1 year using  "~/Dropbox/Winnebago/ESM/intermediate/ihs.dta"
	
	drop _merge
	
	// coding missing as zero so it sums. But missing means did not find data 
	replace idv_transaction_value = 0 if idv_transaction_value == .
	replace ihs638_transaction_value = 0 if ihs638_transaction_value == .
	replace transaction_value = 0 if transaction_value == .
		
	gen total_transactions_tribe = transaction_value + idv_transaction_value
	
	set obs `=_N+1'
	replace year = 2008 if year == .
	
	set obs `=_N+1'
	replace year = 2010 if year == .
	
	set obs `=_N+1'
	replace year = 2011 if year == .
	
	set obs `=_N+1'
	replace year = 2012 if year == .
	
	set obs `=_N+1'
	replace year = 2013 if year == .
	
	set obs `=_N+1'
	replace year = 2014 if year == .
	
	set obs `=_N+1'
	replace year = 2015 if year == .
	
	set obs `=_N+1'
	replace year = 2016 if year == .
	
	set obs `=_N+1'
	replace year = 2017 if year == .
	
	// coding missing as zero so it sums. But missing means did not find data 
	replace idv_transaction_value = 0 if idv_transaction_value == .
	replace ihs638_transaction_value = 0 if ihs638_transaction_value == .
	replace transaction_value = 0 if transaction_value == .
	
	sort year 
	
	#delimit;
	
	graph bar total_transactions_tribe  ihs638_transaction_value, over(year , lab(ang(v))) stack legend(order(1 "Winnebago Tribe Award Obligations" 2 "IHS 638 Direct Payments"))
	
	title( 
			"Figure [E016]: Winnebago Tribe Total Award Obligations & IHS 638 Payments", size(medium))
			subtitle("1999-2022", size(small))
			note("Source: FPDS & FSRS accessed via HigherGov & FRED" ///
			"Note: Sub Award obligations data availability begins in 2010 due to the implementation schedule of the Federal Funding Accountability and Transparency Act (FFATA)." ///
			"This means that we cannot reliably capture Sub Award Obligations prior to 2010 even though they may exist." ///
			"This combines all award obligations - Prime, Sub and IDV Awards for Winnebago Tribe of Nebraska only." ///
			"This additionally includes IHS 638 direct payments to the Tribe as its own category" ///
			"Preliminary Draft - Subject to Revision")
			ylabel(0 "$0" 20000000 "$20M" 40000000 "$40M" 60000000 "$60M")
			xsize(11) ysize(8)
			ytitle("nominal dollars")
	
	;
	#delimit cr
	
	graph export "~/Dropbox/Winnebago/ESM/results/[E016]awardandcompacttribe.pdf", replace
	
} // awardandcompacttribe

if $awardtribe==1{
	
	// Winnebago Tribe only
	// PRIME
	use "~/Dropbox/Winnebago/ESM/clean/prime file.dta", clear
	
	keep if tribe_recipient == 1
	collapse (sum) transaction_value, by(year)
	
	save "~/Dropbox/Winnebago/ESM/intermediate/prime.dta", replace
	
	// IDV
	use "~/Dropbox/Winnebago/ESM/clean/idv file.dta", clear
	
	keep if tribe_recipient == 1
	collapse (sum) idv_transaction_value, by(year)
	
	save "~/Dropbox/Winnebago/ESM/intermediate/idv.dta", replace
	
	// COMBINE
	
	use "~/Dropbox/Winnebago/ESM/intermediate/prime.dta", clear
	
	merge 1:1 year using  "~/Dropbox/Winnebago/ESM/intermediate/idv.dta"
	
	drop _merge

	// coding missing as zero so it sums. But missing means did not find data 
	replace idv_transaction_value = 0 if idv_transaction_value == .
	replace transaction_value = 0 if transaction_value == .
		
	gen total_transactions_tribe = transaction_value + idv_transaction_value
	
	set obs `=_N+1'
	replace year = 2008 if year == .
	
	// coding missing as zero so it sums. But missing means did not find data 
	replace idv_transaction_value = 0 if idv_transaction_value == .
	replace transaction_value = 0 if transaction_value == .
	
	sort year 
	
	#delimit;
	
	graph bar total_transactions_tribe  , over(year) 
	
	title( 
			"Figure [E017]: Winnebago Tribe Total Award Obligations", size(medium))
			subtitle("1999-2009", size(small))
			note("Source: FPDS & FSRS accessed via HigherGov & FRED" ///
			"Note: this combines all award obligations - Prime, Sub and IDV Awards for Winnebago Tribe of Nebraska only." ///
			"Winnebago Tribe did not receive any award obligations past 2009" ///
			"Preliminary Draft - Subject to Revision")
			ylabel(0 "$0" 500000 "$.5M" 1000000 "$1M" 1500000 "$1.5M" 2000000 "$2M")
			xsize(11) ysize(8)
			ytitle("nominal dollars")
	
	;
	#delimit cr
	
	graph export "~/Dropbox/Winnebago/ESM/results/[E017]awardtribe.pdf", replace
	
} // awardtribe

if $placefunding==1{
	
	use "~/Dropbox/Winnebago/ESM/clean/prime file.dta", clear
	
	drop if tribe_recipient == 1 // to isolate HCI only
	
	// cleaning up state and city names
	
	replace performance_country_name = "Not given" if performance_country_name == "NULL"
	replace performance_state_name = "Not given" if performance_state_name == "NULL"
	replace primary_place_of_performance_cit = "Not given" if primary_place_of_performance_cit == "NULL"
	
	replace performance_country_name = proper(performance_country_name)
	replace performance_country_name = itrim(performance_country_name) // remove any potential empty space at end of awardee name
	replace performance_country_name = trim(performance_country_name)  // remove any potential empty space at other end of awardee name
	
	replace performance_state_name = proper(performance_state_name)
	replace performance_state_name = itrim(performance_state_name) // remove any potential empty space at end of awardee name
	replace performance_state_name = trim(performance_state_name)  // remove any potential empty space at other end of awardee name
	
	replace primary_place_of_performance_cit = proper(primary_place_of_performance_cit)
	replace primary_place_of_performance_cit = itrim(primary_place_of_performance_cit) // remove any potential empty space at end of awardee name
	replace primary_place_of_performance_cit = trim(primary_place_of_performance_cit)  // remove any potential empty space at other end of awardee name
	
	collapse (sum) transaction_value i_transaction_value, by( performance_country_name performance_state_name  primary_place_of_performance_cit )
	
	order performance_country_name performance_state_name primary_place_of_performance_cit transaction_value
	
	egen total_obligations = total(transaction_value)
	
	gen share_obligations_by_performance = transaction_value/total_obligations
	
	egen i_total_obligations = total(i_transaction_value)
	
	gen i_share_obligations_by_perfo = i_transaction_value/i_total_obligations
	
	gsort i_share_obligations_by_perfo
	
	order performance_country_name performance_state_name primary_place_of_performance_cit transaction_value i_transaction_value share_obligations_by_performance i_share_obligations_by_perfo
	
	export excel using "~/Dropbox/Winnebago/ESM/results/hci obligations by place of performance.xlsx", firstrow(variables) replace

} // placefunding

if $placefunding8a==1{
	
	use "~/Dropbox/Winnebago/ESM/clean/prime file.dta", clear
	
	drop if tribe_recipient == 1 // to isolate HCI only
	
	// to isolate HCI 8a revenue only
	
	keep if setaside == "8(a)"
	
	// cleaning up state and city names
	
	replace performance_country_name = "Not given" if performance_country_name == "NULL"
	replace performance_state_name = "Not given" if performance_state_name == "NULL"
	replace primary_place_of_performance_cit = "Not given" if primary_place_of_performance_cit == "NULL"
	
	replace performance_country_name = proper(performance_country_name)
	replace performance_country_name = itrim(performance_country_name) // remove any potential empty space at end of awardee name
	replace performance_country_name = trim(performance_country_name)  // remove any potential empty space at other end of awardee name
	
	replace performance_state_name = proper(performance_state_name)
	replace performance_state_name = itrim(performance_state_name) // remove any potential empty space at end of awardee name
	replace performance_state_name = trim(performance_state_name)  // remove any potential empty space at other end of awardee name
	
	replace primary_place_of_performance_cit = proper(primary_place_of_performance_cit)
	replace primary_place_of_performance_cit = itrim(primary_place_of_performance_cit) // remove any potential empty space at end of awardee name
	replace primary_place_of_performance_cit = trim(primary_place_of_performance_cit)  // remove any potential empty space at other end of awardee name
	
	collapse (sum) transaction_value i_transaction_value, by( performance_country_name performance_state_name  primary_place_of_performance_cit )
	
	order performance_country_name performance_state_name primary_place_of_performance_cit transaction_value
	
	egen total_obligations = total(transaction_value)
	
	gen share_obligations_by_performance = transaction_value/total_obligations
	
	egen i_total_obligations = total(i_transaction_value)
	
	gen i_share_obligations_by_perfo = i_transaction_value/i_total_obligations
	
	gsort i_share_obligations_by_perfo
	
	order performance_country_name performance_state_name primary_place_of_performance_cit transaction_value i_transaction_value share_obligations_by_performance i_share_obligations_by_perfo
	
	export excel using "~/Dropbox/Winnebago/ESM/results/hci obligations by place of performance 8a.xlsx", firstrow(variables) replace
	
} // placefunding8a

capture log close hcipreliminaryfigures
