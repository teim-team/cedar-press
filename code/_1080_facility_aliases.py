#!/usr/bin/env python3
"""Curated map for code/1080_sec_gaming_facility_revenue.py.

Two hand-built tables. Neither is derived from the data; both are rulings, and
each entry names the property as the FILER writes it, not as Cedar writes it.

FILERS   CIK (unpadded) -> the registrant, and what it was to the property.
         Only CIKs listed here are read. A filer absent from this map is not a
         judgement that it has nothing; it is a statement that nobody has looked.

ALIASES  the string a filer uses -> the facility_id in data/clean/gaming_facilities.csv.
         `on_indian_lands` is N for a property a tribal instrumentality owns that
         is NOT Indian-lands gaming (Mohegan Sun Pocono is a Pennsylvania
         racino), and NON_US for a foreign property. Those rows are kept and
         labelled rather than dropped, because dropping them would make a
         segment table look as though it adds up to the tribal properties alone.

NOTE ON NEAR-DUPLICATE FACILITY IDS. gaming_facilities.csv carries the same
property twice for several of these (a `CCP-` row from Casino City and a `VP-`
row from the voting-patterns canonical list), and `duplicate_of_facility_id` is
blank on both - measured 2026-09-02. This map keys to the CCP- row wherever one
exists, because that is the row carrying has_revenue_bound and the capacity
observations. A count of "facilities reached" off this map is a count of
PROPERTIES, and the near-duplicate ids are listed in NEAR_DUPLICATE_IDS so no
consumer double-counts one property as two.
"""

FILERS = {
    # tribal instrumentalities that are themselves SEC registrants (public debt)
    "1005276": {"name": "Mohegan Tribal Gaming Authority", "role": "OPERATOR_TRIBAL_INSTRUMENTALITY"},
    "1296785": {"name": "Seneca Gaming Corporation", "role": "OPERATOR_TRIBAL_INSTRUMENTALITY"},
    "1296783": {"name": "Seneca Territory Gaming Corporation", "role": "OPERATOR_TRIBAL_INSTRUMENTALITY"},
    "1296784": {"name": "Seneca Niagara Falls Gaming Corporation", "role": "OPERATOR_TRIBAL_INSTRUMENTALITY"},
    "1296786": {"name": "Seneca Erie Gaming Corporation", "role": "OPERATOR_TRIBAL_INSTRUMENTALITY"},
    # public managers / developers of tribal casinos
    "1071255": {"name": "Lakes Entertainment, Inc.", "role": "DEVELOPER_MANAGER"},
    "1653653": {"name": "Red Rock Resorts, Inc. (Station Casinos)", "role": "MANAGER"},
    "891482": {"name": "Full House Resorts, Inc.", "role": "MANAGER"},
    "277058": {"name": "Nevada Gold & Casinos, Inc.", "role": "DEVELOPER_MANAGER"},
    "906780": {"name": "Empire Resorts, Inc.", "role": "DEVELOPER_MANAGER"},
    "318291": {"name": "Venture Catalyst Incorporated", "role": "MANAGER"},
    "15847": {"name": "Butler National Corporation", "role": "MANAGER"},
    "911147": {"name": "Century Casinos, Inc.", "role": "MANAGER"},
    # holder of a relinquishment / participation interest in a tribal casino's revenues
    "1028911": {"name": "Waterford Gaming, L.L.C.", "role": "RELINQUISHMENT_INTEREST_HOLDER"},
    # large operators that have held tribal management contracts
    "858339": {"name": "Caesars Entertainment Corporation", "role": "MANAGER"},
    "1590895": {"name": "Caesars Entertainment, Inc.", "role": "MANAGER"},
}

# alias -> (facility_id, tribe as Cedar writes it, state, on_indian_lands)
ALIASES = {
    # --- Mohegan Tribal Gaming Authority
    "Mohegan Sun Pocono": ("VP-0034", "Mohegan Tribe", "PA", "N"),
    "Mohegan Sun at Pocono Downs": ("VP-0034", "Mohegan Tribe", "PA", "N"),
    "Pocono Downs": ("VP-0034", "Mohegan Tribe", "PA", "N"),
    "Mohegan Sun": ("CCP-45100", "Mohegan Tribe", "CT", "Y"),
    "ilani Casino Resort": ("CCP-656400", "Cowlitz Indian Tribe", "WA", "Y"),
    "ilani Casino": ("CCP-656400", "Cowlitz Indian Tribe", "WA", "Y"),
    "Paragon Casino Resort": ("CCP-12800", "Tunica-Biloxi Tribe of Louisiana", "LA", "Y"),
    "MGE Niagara Resorts": ("", "", "ON", "NON_US"),
    "Niagara Fallsview Casino Resort": ("", "", "ON", "NON_US"),
    # --- Seneca Gaming Corporation
    "Seneca Niagara Casino and Hotel": ("CCP-565900", "Seneca Nation of Indians", "NY", "Y"),
    "Seneca Niagara Resort & Casino": ("CCP-565900", "Seneca Nation of Indians", "NY", "Y"),
    "Seneca Niagara Casino": ("CCP-565900", "Seneca Nation of Indians", "NY", "Y"),
    "Seneca Allegany Casino and Hotel": ("CCP-635600", "Seneca Nation of Indians", "NY", "Y"),
    "Seneca Allegany Resort & Casino": ("CCP-635600", "Seneca Nation of Indians", "NY", "Y"),
    "Seneca Allegany Casino": ("CCP-635600", "Seneca Nation of Indians", "NY", "Y"),
    "Seneca Buffalo Creek Casino": ("CCP-824100", "Seneca Nation of Indians", "NY", "Y"),
    # --- Lakes Entertainment / Grand Casinos
    "Red Hawk Casino": ("CCP-743100", "Shingle Springs Band of Miwok Indians", "CA", "Y"),
    "Four Winds Casino Resort": ("CCP-639000", "Pokagon Band of Potawatomi Indians", "MI", "Y"),
    "Four Winds Casino": ("CCP-639000", "Pokagon Band of Potawatomi Indians", "MI", "Y"),
    "Grand Casino Coushatta": ("CCP-38800", "Coushatta Tribe of Louisiana", "LA", "Y"),
    "Grand Casino Avoyelles": ("CCP-12800", "Tunica-Biloxi Tribe of Louisiana", "LA", "Y"),
    "Grand Casino Hinckley": ("CCP-66500", "Mille Lacs Band of Ojibwe", "MN", "Y"),
    "Grand Casino Mille Lacs": ("CCP-66600", "Mille Lacs Band of Ojibwe", "MN", "Y"),
    "Cimarron Casino": ("CCP-304800", "Iowa Tribe of Oklahoma", "OK", "Y"),
    "Jamul Casino": ("CCP-775700", "Jamul Indian Village", "CA", "Y"),
    "Hollywood Casino Jamul": ("CCP-775700", "Jamul Indian Village", "CA", "Y"),
    # --- Red Rock Resorts / Station Casinos
    "Graton Resort & Casino": ("CCP-638700", "Federated Indians of Graton Rancheria", "CA", "Y"),
    "Graton Resort and Casino": ("CCP-638700", "Federated Indians of Graton Rancheria", "CA", "Y"),
    "Graton Resort": ("CCP-638700", "Federated Indians of Graton Rancheria", "CA", "Y"),
    "Graton Casino": ("CCP-638700", "Federated Indians of Graton Rancheria", "CA", "Y"),
    "Gun Lake Casino": ("CCP-637500", "Match-e-be-nash-she-wish Band of Pottawatomi", "MI", "Y"),
    "Gun Lake": ("CCP-637500", "Match-e-be-nash-she-wish Band of Pottawatomi", "MI", "Y"),
    # --- Full House Resorts
    "FireKeepers Casino Hotel": ("CCP-658400", "Nottawaseppi Huron Band of Potawatomi Indians", "MI", "Y"),
    "FireKeepers Casino": ("CCP-658400", "Nottawaseppi Huron Band of Potawatomi Indians", "MI", "Y"),
    "FireKeepers": ("CCP-658400", "Nottawaseppi Huron Band of Potawatomi Indians", "MI", "Y"),
    "Buffalo Thunder Resort & Casino": ("CCP-649400", "Pueblo of Pojoaque", "NM", "Y"),
    "Buffalo Thunder Resort": ("CCP-649400", "Pueblo of Pojoaque", "NM", "Y"),
    "Buffalo Thunder": ("CCP-649400", "Pueblo of Pojoaque", "NM", "Y"),
    # --- Venture Catalyst
    "Barona Valley Ranch Resort & Casino": ("CCP-41700", "Barona Band of Mission Indians", "CA", "Y"),
    "Barona Valley Ranch": ("CCP-41700", "Barona Band of Mission Indians", "CA", "Y"),
    "Barona Casino": ("CCP-41700", "Barona Band of Mission Indians", "CA", "Y"),
    # --- Butler National
    "Stables Casino": ("CCP-305300", "Modoc Tribe of Oklahoma / Miami Tribe of Oklahoma", "OK", "Y"),
    "The Stables": ("CCP-305300", "Modoc Tribe of Oklahoma / Miami Tribe of Oklahoma", "OK", "Y"),
    # --- Nevada Gold & Casinos
    "Harrah" + chr(39) + "s Northern California": ("VP-0087", "Buena Vista Rancheria of Me-Wuk Indians", "CA", "Y"),
    "Buena Vista Rancheria": ("VP-0087", "Buena Vista Rancheria of Me-Wuk Indians", "CA", "Y"),
    # --- others named in the corpus
    "Turning Stone Resort Casino": ("CCP-44400", "Oneida Indian Nation of New York", "NY", "Y"),
    "Turning Stone": ("CCP-44400", "Oneida Indian Nation of New York", "NY", "Y"),
    "Chukchansi Gold Resort & Casino": ("CCP-595800", "Picayune Rancheria of the Chukchansi Indians", "CA", "Y"),
    "Chukchansi Gold": ("CCP-595800", "Picayune Rancheria of the Chukchansi Indians", "CA", "Y"),
    "River Rock Casino": ("CCP-563100", "Dry Creek Rancheria Band of Pomo Indians", "CA", "Y"),
    "North Fork Casino": ("VP-0083", "North Fork Rancheria of Mono Indians", "CA", "Y"),
}

# same property, two rows in gaming_facilities.csv, duplicate_of_facility_id blank on both
NEAR_DUPLICATE_IDS = {
    "CCP-565900": "VP-0029",
    "CCP-635600": "VP-0030",
    "CCP-639000": "VP-0295 / CEDAR-FAC-000013",
    "CCP-305300": "VP-0153",
}
