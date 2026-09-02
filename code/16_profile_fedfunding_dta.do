*! 16_profile_fedfunding_dta.do
*! Cedar Press -- profile LINEAGE A cleaned Stata files (pyreadstat cannot open them).
*! Read-only on the source .dta; writes CSV summaries into
*! Cedar Press/data/raw/external/federal_funding/.
clear all
set more off
version 17

local ROOT "C:/Users/esm247/Desktop/Cedar Press"
local OUTD "`ROOT'/data/raw/external/federal_funding"
cap mkdir "`OUTD'"

foreach V in corrtd orig {
    if "`V'"=="corrtd" local F "`ROOT'/Federal Spending/clean/fed_funding_data_clean_corrtd.dta"
    if "`V'"=="orig"   local F "`ROOT'/Federal Spending/clean/fed_funding_data_clean.dta"

    display as text "==================== `V' : `F'"
    use "`F'", clear
    describe, short
    display as result "ROWS_`V' = " _N

    * ---- column list
    preserve
        describe, replace clear
        export delimited using "`OUTD'/lineageA_dta_`V'_columns.csv", replace
    restore

    * ---- distinct counts
    foreach v in recipient_uei recipient_duns recipient_name Tribe {
        cap confirm variable `v'
        if _rc==0 {
            preserve
                keep if `v'!=""
                bysort `v': keep if _n==1
                display as result "DISTINCT_`v'_`V' = " _N
            restore
        }
    }
    cap confirm variable tribe_id
    if _rc==0 {
        preserve
            keep if tribe_id<.
            bysort tribe_id: keep if _n==1
            display as result "DISTINCT_tribe_id_`V' = " _N
        restore
    }
    cap confirm variable flag
    if _rc==0 {
        tab flag, missing
    }

    * ---- totals by fiscal year x assistance type
    preserve
        gen byte one = 1
        collapse (sum) federal_action_obligation total_obligated_amount rows=one, ///
                 by(action_date_fiscal_year assistance_type_code assistance_type_descript flag)
        export delimited using "`OUTD'/lineageA_dta_`V'_year_atype.csv", replace
    restore

    * ---- totals by tribe x fiscal year (for cross-lineage comparison)
    preserve
        gen byte one = 1
        collapse (sum) federal_action_obligation rows=one, ///
                 by(tribe_id action_date_fiscal_year flag)
        export delimited using "`OUTD'/lineageA_dta_`V'_tribe_year.csv", replace
    restore

    * ---- tribe_id -> example name key
    preserve
        keep tribe_id Tribe recipient_state_code
        bysort tribe_id: keep if _n==1
        export delimited using "`OUTD'/lineageA_dta_`V'_tribe_key.csv", replace
    restore

    * ---- identifier harvest inputs (UEI/DUNS/name/geo)
    preserve
        gen byte one = 1
        collapse (sum) obl=federal_action_obligation n_awards=one ///
                 (min) first_year=action_date_fiscal_year ///
                 (max) last_year=action_date_fiscal_year, ///
                 by(recipient_uei recipient_duns recipient_name recipient_state_code ///
                    recipient_city_name recipient_zip_code)
        export delimited using "`OUTD'/lineageA_dta_`V'_identifiers.csv", replace
    restore

    * ---- assistance types present, with recipient counts
    preserve
        gen byte one = 1
        collapse (sum) obl=federal_action_obligation rows=one, ///
                 by(assistance_type_code assistance_type_descript)
        export delimited using "`OUTD'/lineageA_dta_`V'_atype.csv", replace
    restore

    * ---- state coverage
    preserve
        gen byte one = 1
        collapse (sum) obl=federal_action_obligation rows=one, by(recipient_state_code)
        export delimited using "`OUTD'/lineageA_dta_`V'_state.csv", replace
    restore
}
display as result "PROFILE_DONE"
