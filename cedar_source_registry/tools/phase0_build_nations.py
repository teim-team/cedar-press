#!/usr/bin/env python3
"""Phase 0 — nation crosswalk stub.

Writes nations.jsonl (one row per nation referenced by the registry) and adds
`nation_ids` + `nation_scope` to every sources.jsonl row.

Scope note (recorded in PHASE_REPORT): the brief calls for one row per
federally recognized tribe from the BIA list (575 entities per the 2026-01-30
Federal Register notice). This environment's egress policy blocks fetching the
BIA/Federal Register list, so this stub covers every nation the registry
references, keyed to its BIA-list identity. `bia_name` values are transcribed
from model knowledge of the list, flagged `name_verified_against_list: false`
until the list can be fetched and diffed. The stub's purpose — one stable id
per nation so three phases don't accumulate inconsistent name strings — is met
for every row in the registry. The remaining ~465 unreferenced entities are a
mechanical import once egress allows.

Conventions:
  - nation_id `bia:<slug>` = an entity on the BIA list.
  - `bia:minnesota-chippewa-tribe--<band>` = a component reservation of the
    Minnesota Chippewa Tribe (one BIA-listed entity); parent_nation_id points
    at the parent. Cedar needs band-level identity; the BIA list does not
    provide it.
  - nation_id `nonbia:<slug>` = a nation the registry references that is NOT
    on the BIA list (state-recognized or unrecognized); recognition says which.
  - ANCSA corporations are not nations and get no nation_id; ANC sources map
    to nation_ids [] with nation_scope regional.
  - nation_ids on a source row mean "the nation(s) this source program is
    scoped to" — never an ownership assertion about any listed business.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (slug, bia_name, extra name variants, states)
BIA = [
    ("tulalip-tribes", "Tulalip Tribes of Washington", ["Tulalip Tribes"], ["WA"]),
    ("muscogee-creek-nation", "The Muscogee (Creek) Nation", ["Muscogee (Creek) Nation", "Muscogee Nation"], ["OK"]),
    ("fallon-paiute-shoshone", "Fallon Paiute-Shoshone Tribe of the Fallon Reservation and Colony, Nevada", ["Fallon Paiute-Shoshone Tribe"], ["NV"]),
    ("mechoopda", "Mechoopda Indian Tribe of Chico Rancheria, California", ["Mechoopda Indian Tribe of Chico Rancheria"], ["CA"]),
    ("wampanoag-aquinnah", "Wampanoag Tribe of Gay Head (Aquinnah)", ["Aquinnah Wampanoag"], ["MA"]),
    ("kenaitze", "Kenaitze Indian Tribe", [], ["AK"]),
    ("pamunkey", "Pamunkey Indian Tribe", [], ["VA"]),
    ("forest-county-potawatomi", "Forest County Potawatomi Community, Wisconsin", ["Forest County Potawatomi Community"], ["WI"]),
    ("nez-perce", "Nez Perce Tribe", [], ["ID"]),
    ("chickasaw-nation", "The Chickasaw Nation", ["Chickasaw Nation"], ["OK"]),
    ("grand-ronde", "Confederated Tribes of the Grand Ronde Community of Oregon", ["Confederated Tribes of Grand Ronde"], ["OR"]),
    ("three-affiliated-tribes", "Three Affiliated Tribes of the Fort Berthold Reservation, North Dakota", ["MHA Nation", "Mandan, Hidatsa and Arikara Nation", "Mandan, Hidatsa & Arikara Nation", "Three Affiliated Tribes"], ["ND"]),
    ("standing-rock-sioux", "Standing Rock Sioux Tribe of North & South Dakota", ["Standing Rock Sioux Tribe"], ["ND", "SD"]),
    ("muckleshoot", "Muckleshoot Indian Tribe", [], ["WA"]),
    ("salt-river-pima-maricopa", "Salt River Pima-Maricopa Indian Community of the Salt River Reservation, Arizona", ["Salt River Pima-Maricopa Indian Community"], ["AZ"]),
    ("oneida-nation-wi", "Oneida Nation", ["Oneida Nation of Wisconsin", "Oneida Tribe of Indians of Wisconsin"], ["WI"]),
    ("umatilla", "Confederated Tribes of the Umatilla Indian Reservation", ["CTUIR"], ["OR"]),
    ("warm-springs", "Confederated Tribes of the Warm Springs Reservation of Oregon", ["Confederated Tribes of Warm Springs"], ["OR"]),
    ("puyallup", "Puyallup Tribe of the Puyallup Reservation", ["Puyallup Tribe of Indians"], ["WA"]),
    ("blackfeet", "Blackfeet Tribe of the Blackfeet Indian Reservation of Montana", ["Blackfeet Nation"], ["MT"]),
    ("poarch-band", "Poarch Band of Creek Indians", [], ["AL"]),
    ("salish-kootenai", "Confederated Salish and Kootenai Tribes of the Flathead Reservation", ["Confederated Salish and Kootenai Tribes", "CSKT"], ["MT"]),
    ("navajo-nation", "Navajo Nation, Arizona, New Mexico, & Utah", ["Navajo Nation"], ["AZ", "NM", "UT"]),
    ("cherokee-nation", "Cherokee Nation", [], ["OK"]),
    ("colville", "Confederated Tribes of the Colville Reservation", [], ["WA"]),
    ("spokane", "Spokane Tribe of the Spokane Reservation", ["Spokane Tribe of Indians"], ["WA"]),
    ("southern-ute", "Southern Ute Indian Tribe of the Southern Ute Reservation", ["Southern Ute Indian Tribe"], ["CO"]),
    ("rosebud-sioux", "Rosebud Sioux Tribe of the Rosebud Indian Reservation, South Dakota", ["Rosebud Sioux Tribe"], ["SD"]),
    ("yurok", "Yurok Tribe of the Yurok Reservation, California", ["Yurok Tribe"], ["CA"]),
    ("ute-indian-tribe", "Ute Indian Tribe of the Uintah & Ouray Reservation, Utah", ["Ute Indian Tribe of the Uintah and Ouray Reservation", "Northern Ute Tribe"], ["UT"]),
    ("sault-ste-marie", "Sault Ste. Marie Tribe of Chippewa Indians, Michigan", ["Sault Ste. Marie Tribe of Chippewa Indians", "Sault Tribe"], ["MI"]),
    ("eastern-band-cherokee", "Eastern Band of Cherokee Indians", ["EBCI"], ["NC"]),
    ("tohono-oodham", "Tohono O'odham Nation of Arizona", ["Tohono O'odham Nation", "Tohono O’odham Nation"], ["AZ"]),
    ("choctaw-nation-oklahoma", "Choctaw Nation of Oklahoma", [], ["OK"]),
    ("pawnee-nation", "Pawnee Nation of Oklahoma", [], ["OK"]),
    ("otoe-missouria", "Otoe-Missouria Tribe of Indians, Oklahoma", ["Otoe-Missouria Tribe"], ["OK"]),
    ("minnesota-chippewa-tribe", "Minnesota Chippewa Tribe, Minnesota", ["Minnesota Chippewa Tribe", "MCT"], ["MN"]),
    ("lummi", "Lummi Tribe of the Lummi Reservation", ["Lummi Nation"], ["WA"]),
    ("coeur-dalene", "Coeur d'Alene Tribe", ["Coeur d’Alene Tribe"], ["ID"]),
    ("shoshone-bannock", "Shoshone-Bannock Tribes of the Fort Hall Reservation", ["Shoshone-Bannock Tribes"], ["ID"]),
    ("sisseton-wahpeton-oyate", "Sisseton-Wahpeton Oyate of the Lake Traverse Reservation, South Dakota", ["Sisseton Wahpeton Oyate"], ["SD"]),
    ("mississippi-choctaw", "Mississippi Band of Choctaw Indians", [], ["MS"]),
    ("pyramid-lake-paiute", "Pyramid Lake Paiute Tribe of the Pyramid Lake Reservation, Nevada", ["Pyramid Lake Paiute Tribe"], ["NV"]),
    ("red-cliff-chippewa", "Red Cliff Band of Lake Superior Chippewa Indians of Wisconsin", ["Red Cliff Band of Lake Superior Chippewa"], ["WI"]),
    ("bad-river-chippewa", "Bad River Band of the Lake Superior Tribe of Chippewa Indians of the Bad River Reservation, Wisconsin", ["Bad River Band of Lake Superior Chippewa"], ["WI"]),
    ("cheyenne-river-sioux", "Cheyenne River Sioux Tribe of the Cheyenne River Reservation, South Dakota", ["Cheyenne River Sioux Tribe"], ["SD"]),
    ("menominee", "Menominee Indian Tribe of Wisconsin", [], ["WI"]),
    ("osage-nation", "Osage Nation", [], ["OK"]),
    ("citizen-potawatomi", "Citizen Potawatomi Nation, Oklahoma", ["Citizen Potawatomi Nation"], ["OK"]),
    ("catawba", "Catawba Indian Nation", ["Catawba Nation"], ["SC"]),
    ("keweenaw-bay", "Keweenaw Bay Indian Community, Michigan", ["Keweenaw Bay Indian Community"], ["MI"]),
    ("native-village-of-eyak", "Native Village of Eyak (Cordova)", ["Native Village of Eyak"], ["AK"]),
    ("snoqualmie", "Snoqualmie Indian Tribe", [], ["WA"]),
    ("penobscot", "Penobscot Nation", [], ["ME"]),
    ("grand-traverse-band", "Grand Traverse Band of Ottawa and Chippewa Indians, Michigan", ["Grand Traverse Band of Ottawa and Chippewa Indians"], ["MI"]),
    ("little-traverse-bay-bands", "Little Traverse Bay Bands of Odawa Indians, Michigan", ["Little Traverse Bay Bands of Odawa Indians"], ["MI"]),
    ("cowlitz", "Cowlitz Indian Tribe", [], ["WA"]),
    ("tolowa-dee-ni", "Tolowa Dee-ni' Nation, California", ["Tolowa Dee-ni' Nation", "Tolowa Dee-ni’ Nation"], ["CA"]),
    ("hoopa-valley", "Hoopa Valley Tribe, California", ["Hoopa Valley Tribe"], ["CA"]),
    ("bishop-paiute", "Bishop Paiute Tribe", ["Paiute-Shoshone Indians of the Bishop Community of the Bishop Colony"], ["CA"]),
    ("mashantucket-pequot", "Mashantucket Pequot Indian Tribe", ["Mashantucket Pequot Tribal Nation"], ["CT"]),
    ("quinault", "Quinault Indian Nation", [], ["WA"]),
    ("yakama", "Confederated Tribes and Bands of the Yakama Nation", ["Yakama Nation"], ["WA"]),
    ("yavapai-apache", "Yavapai-Apache Nation of the Camp Verde Indian Reservation, Arizona", ["Yavapai-Apache Nation"], ["AZ"]),
    ("spirit-lake", "Spirit Lake Tribe, North Dakota", ["Spirit Lake Nation", "Spirit Lake Tribe"], ["ND"]),
    ("northern-cheyenne", "Northern Cheyenne Tribe of the Northern Cheyenne Indian Reservation, Montana", ["Northern Cheyenne Tribe"], ["MT"]),
    ("fort-peck", "Assiniboine and Sioux Tribes of the Fort Peck Indian Reservation, Montana", ["Assiniboine and Sioux Tribes of the Fort Peck Indian Reservation", "Fort Peck Tribes"], ["MT"]),
    ("eastern-shoshone", "Eastern Shoshone Tribe of the Wind River Reservation, Wyoming", ["Eastern Shoshone Tribe"], ["WY"]),
    ("northern-arapaho", "Northern Arapaho Tribe of the Wind River Reservation, Wyoming", ["Northern Arapaho Tribe"], ["WY"]),
    ("karuk", "Karuk Tribe", [], ["CA"]),
    ("ute-mountain-ute", "Ute Mountain Ute Tribe", [], ["CO", "NM", "UT"]),
    ("klamath", "Klamath Tribes", ["The Klamath Tribes"], ["OR"]),
    ("oglala-sioux", "Oglala Sioux Tribe", [], ["SD"]),
    ("chippewa-cree", "Chippewa Cree Indians of the Rocky Boy's Reservation, Montana", ["Chippewa Cree Tribe of the Rocky Boy's Reservation", "Chippewa Cree Tribe of the Rocky Boy’s Reservation"], ["MT"]),
    ("seminole-nation-oklahoma", "Seminole Nation of Oklahoma", [], ["OK"]),
    ("kiowa", "Kiowa Indian Tribe of Oklahoma", ["Kiowa Tribe"], ["OK"]),
    ("comanche", "Comanche Nation, Oklahoma", ["Comanche Nation"], ["OK"]),
    ("cheyenne-and-arapaho", "Cheyenne and Arapaho Tribes, Oklahoma", ["Cheyenne and Arapaho Tribes"], ["OK"]),
    ("wichita-affiliated", "Wichita and Affiliated Tribes (Wichita, Keechi, Waco & Tawakonie), Oklahoma", ["Wichita and Affiliated Tribes"], ["OK"]),
    ("swinomish", "Swinomish Indian Tribal Community", [], ["WA"]),
    ("red-lake", "Red Lake Band of Chippewa Indians, Minnesota", ["Red Lake Nation", "Red Lake Band of Chippewa Indians"], ["MN"]),
    ("mashpee-wampanoag", "Mashpee Wampanoag Tribe", [], ["MA"]),
    ("lumbee", "Lumbee Tribe of North Carolina", [], ["NC"]),
    ("omaha-tribe", "Omaha Tribe of Nebraska", [], ["NE"]),
    ("crow-tribe", "Crow Tribe of Montana", ["Crow Tribe of Indians", "Apsaalooke Nation"], ["MT"]),
    ("san-carlos-apache", "San Carlos Apache Tribe of the San Carlos Reservation, Arizona", ["San Carlos Apache Tribe"], ["AZ"]),
    ("tlingit-haida", "Central Council of the Tlingit & Haida Indian Tribes", ["Central Council of the Tlingit and Haida Indian Tribes of Alaska", "Tlingit & Haida"], ["AK"]),
    ("colorado-river-indian-tribes", "Colorado River Indian Tribes of the Colorado River Indian Reservation, Arizona and California", ["Colorado River Indian Tribes", "CRIT"], ["AZ", "CA"]),
    ("pueblo-of-laguna", "Pueblo of Laguna, New Mexico", ["Pueblo of Laguna"], ["NM"]),
    ("prairie-island", "Prairie Island Indian Community in the State of Minnesota", ["Prairie Island Indian Community"], ["MN"]),
    ("saint-regis-mohawk", "Saint Regis Mohawk Tribe", ["St. Regis Mohawk Tribe"], ["NY"]),
    ("ho-chunk", "Ho-Chunk Nation of Wisconsin", ["Ho-Chunk Nation"], ["WI"]),
    ("quapaw", "Quapaw Nation", ["The Quapaw Nation"], ["OK"]),
    ("gila-river", "Gila River Indian Community of the Gila River Indian Reservation, Arizona", ["Gila River Indian Community"], ["AZ"]),
    ("pascua-yaqui", "Pascua Yaqui Tribe of Arizona", ["Pascua Yaqui Tribe"], ["AZ"]),
    ("turtle-mountain-chippewa", "Turtle Mountain Band of Chippewa Indians of North Dakota", ["Turtle Mountain Band of Chippewa Indians"], ["ND"]),
    ("squaxin-island", "Squaxin Island Tribe of the Squaxin Island Reservation", ["Squaxin Island Tribe"], ["WA"]),
    ("chehalis", "Confederated Tribes of the Chehalis Reservation", [], ["WA"]),
    ("nisqually", "Nisqually Indian Tribe", [], ["WA"]),
    ("shoalwater-bay", "Shoalwater Bay Indian Tribe of the Shoalwater Bay Indian Reservation", ["Shoalwater Bay Indian Tribe"], ["WA"]),
    ("skokomish", "Skokomish Indian Tribe", [], ["WA"]),
    # Wave 5.1 Phase 3 expansion sweep (2026-08-27): every tribe checked gets
    # a crosswalk row so negative_findings.jsonl and new sources key cleanly.
    ("hopi", "Hopi Tribe of Arizona", ["Hopi Tribe"], ["AZ"]),
    ("zuni", "Zuni Tribe of the Zuni Reservation, New Mexico", ["Pueblo of Zuni", "Zuni Tribe"], ["NM"]),
    ("acoma", "Pueblo of Acoma, New Mexico", ["Pueblo of Acoma"], ["NM"]),
    ("isleta", "Pueblo of Isleta, New Mexico", ["Pueblo of Isleta"], ["NM"]),
    ("sandia", "Pueblo of Sandia, New Mexico", ["Pueblo of Sandia"], ["NM"]),
    ("santa-clara-pueblo", "Santa Clara Pueblo, New Mexico", ["Santa Clara Pueblo"], ["NM"]),
    ("taos-pueblo", "Pueblo of Taos, New Mexico", ["Taos Pueblo"], ["NM"]),
    ("ohkay-owingeh", "Ohkay Owingeh, New Mexico", ["Ohkay Owingeh"], ["NM"]),
    ("jemez", "Pueblo of Jemez, New Mexico", ["Pueblo of Jemez"], ["NM"]),
    ("santo-domingo", "Santo Domingo Pueblo, New Mexico", ["Santo Domingo Pueblo", "Kewa Pueblo"], ["NM"]),
    ("jicarilla-apache", "Jicarilla Apache Nation, New Mexico", ["Jicarilla Apache Nation"], ["NM"]),
    ("mescalero-apache", "Mescalero Apache Tribe of the Mescalero Reservation, New Mexico", ["Mescalero Apache Tribe"], ["NM"]),
    ("pojoaque", "Pueblo of Pojoaque, New Mexico", ["Pueblo of Pojoaque"], ["NM"]),
    ("san-felipe", "Pueblo of San Felipe, New Mexico", ["Pueblo of San Felipe"], ["NM"]),
    ("tesuque", "Pueblo of Tesuque, New Mexico", ["Pueblo of Tesuque"], ["NM"]),
    ("absentee-shawnee", "Absentee Shawnee Tribe of Indians of Oklahoma", ["Absentee Shawnee Tribe"], ["OK"]),
    ("sac-and-fox-nation", "Sac & Fox Nation, Oklahoma", ["Sac and Fox Nation"], ["OK"]),
    ("iowa-tribe-oklahoma", "Iowa Tribe of Oklahoma", [], ["OK"]),
    ("kickapoo-oklahoma", "Kickapoo Tribe of Oklahoma", [], ["OK"]),
    ("ponca-oklahoma", "The Ponca Tribe of Indians of Oklahoma", ["Ponca Tribe of Indians of Oklahoma"], ["OK"]),
    ("tonkawa", "Tonkawa Tribe of Indians of Oklahoma", ["Tonkawa Tribe"], ["OK"]),
    ("caddo", "Caddo Nation of Oklahoma", ["Caddo Nation"], ["OK"]),
    ("wyandotte", "Wyandotte Nation", [], ["OK"]),
    ("miami-oklahoma", "Miami Tribe of Oklahoma", [], ["OK"]),
    ("shawnee-tribe", "Shawnee Tribe", [], ["OK"]),
    ("eastern-shawnee", "Eastern Shawnee Tribe of Oklahoma", [], ["OK"]),
    ("united-keetoowah", "United Keetoowah Band of Cherokee Indians in Oklahoma", ["United Keetoowah Band of Cherokee Indians"], ["OK"]),
    ("fort-sill-apache", "Fort Sill Apache Tribe of Oklahoma", ["Fort Sill Apache Tribe"], ["OK"]),
    ("delaware-nation", "Delaware Nation, Oklahoma", ["Delaware Nation"], ["OK"]),
    ("prairie-band-potawatomi", "Prairie Band Potawatomi Nation", [], ["KS"]),
    ("pokagon-band", "Pokagon Band of Potawatomi Indians, Michigan and Indiana", ["Pokagon Band of Potawatomi Indians"], ["MI", "IN"]),
    ("gun-lake", "Match-e-be-nash-she-wish Band of Pottawatomi Indians of Michigan", ["Gun Lake Tribe", "Match-E-Be-Nash-She-Wish Band"], ["MI"]),
    ("nottawaseppi-huron", "Nottawaseppi Huron Band of the Potawatomi, Michigan", ["Nottawaseppi Huron Band of the Potawatomi"], ["MI"]),
    ("bay-mills", "Bay Mills Indian Community, Michigan", ["Bay Mills Indian Community"], ["MI"]),
    ("hannahville", "Hannahville Indian Community, Michigan", ["Hannahville Indian Community"], ["MI"]),
    ("lac-vieux-desert", "Lac Vieux Desert Band of Lake Superior Chippewa Indians of Michigan", ["Lac Vieux Desert Band of Lake Superior Chippewa"], ["MI"]),
    ("lac-du-flambeau", "Lac du Flambeau Band of Lake Superior Chippewa Indians of the Lac du Flambeau Reservation of Wisconsin", ["Lac du Flambeau Band of Lake Superior Chippewa"], ["WI"]),
    ("lac-courte-oreilles", "Lac Courte Oreilles Band of Lake Superior Chippewa Indians of Wisconsin", ["Lac Courte Oreilles Band of Lake Superior Chippewa"], ["WI"]),
    ("st-croix-chippewa", "St. Croix Chippewa Indians of Wisconsin", [], ["WI"]),
    ("sokaogon", "Sokaogon Chippewa Community, Wisconsin", ["Sokaogon Chippewa Community", "Mole Lake Band"], ["WI"]),
    ("stockbridge-munsee", "Stockbridge Munsee Community, Wisconsin", ["Stockbridge-Munsee Community"], ["WI"]),
    ("ponca-nebraska", "Ponca Tribe of Nebraska", [], ["NE"]),
    ("santee-sioux", "Santee Sioux Nation, Nebraska", ["Santee Sioux Nation"], ["NE"]),
    ("yankton-sioux", "Yankton Sioux Tribe of South Dakota", ["Yankton Sioux Tribe"], ["SD"]),
    ("lower-brule", "Lower Brule Sioux Tribe of the Lower Brule Reservation, South Dakota", ["Lower Brule Sioux Tribe"], ["SD"]),
    ("san-manuel", "Yuhaaviatam of San Manuel Nation", ["San Manuel Band of Mission Indians"], ["CA"]),
    ("morongo", "Morongo Band of Mission Indians, California", ["Morongo Band of Mission Indians"], ["CA"]),
    ("pechanga", "Pechanga Band of Indians", ["Pechanga Band of Luiseno Mission Indians"], ["CA"]),
    ("agua-caliente", "Agua Caliente Band of Cahuilla Indians of the Agua Caliente Indian Reservation, California", ["Agua Caliente Band of Cahuilla Indians"], ["CA"]),
    ("sycuan", "Sycuan Band of the Kumeyaay Nation", [], ["CA"]),
    ("washoe", "Washoe Tribe of Nevada & California", ["Washoe Tribe of Nevada and California"], ["NV", "CA"]),
    ("reno-sparks", "Reno-Sparks Indian Colony, Nevada", ["Reno-Sparks Indian Colony"], ["NV"]),
    ("alabama-coushatta", "Alabama-Coushatta Tribe of Texas", [], ["TX"]),
    ("coushatta-louisiana", "Coushatta Tribe of Louisiana", [], ["LA"]),
    ("chitimacha", "Chitimacha Tribe of Louisiana", [], ["LA"]),
    ("tunica-biloxi", "Tunica-Biloxi Indian Tribe of Louisiana", ["Tunica-Biloxi Tribe of Louisiana"], ["LA"]),
    ("miccosukee", "Miccosukee Tribe of Indians", ["Miccosukee Tribe of Indians of Florida"], ["FL"]),
    ("mohegan", "Mohegan Tribe of Indians of Connecticut", ["Mohegan Tribe"], ["CT"]),
    ("seneca-nation", "Seneca Nation of Indians", [], ["NY"]),
    ("passamaquoddy", "Passamaquoddy Tribe", [], ["ME"]),
    ("shinnecock", "Shinnecock Indian Nation", [], ["NY"]),
    ("suquamish", "Suquamish Indian Tribe of the Port Madison Reservation", ["Suquamish Tribe"], ["WA"]),
    ("port-gamble-sklallam", "Port Gamble S'Klallam Tribe", [], ["WA"]),
    ("jamestown-sklallam", "Jamestown S'Klallam Tribe", [], ["WA"]),
    ("lower-elwha", "Lower Elwha Tribal Community", ["Lower Elwha Klallam Tribe"], ["WA"]),
    ("makah", "Makah Indian Tribe of the Makah Indian Reservation", ["Makah Tribe"], ["WA"]),
    ("quileute", "Quileute Tribe of the Quileute Reservation", ["Quileute Tribe"], ["WA"]),
    ("nooksack", "Nooksack Indian Tribe", [], ["WA"]),
    ("upper-skagit", "Upper Skagit Indian Tribe", [], ["WA"]),
    ("stillaguamish", "Stillaguamish Tribe of Indians of Washington", ["Stillaguamish Tribe of Indians"], ["WA"]),
    ("siletz", "Confederated Tribes of Siletz Indians of Oregon", ["Confederated Tribes of Siletz Indians", "CTSI"], ["OR"]),
    ("coquille", "Coquille Indian Tribe", [], ["OR"]),
    ("cow-creek", "Cow Creek Band of Umpqua Tribe of Indians", [], ["OR"]),
    # Phase 3 round 2 (2026-08-27)
    ("nambe", "Nambe Pueblo, New Mexico", ["Pueblo of Nambe"], ["NM"]),
    ("picuris", "Picuris Pueblo, New Mexico", ["Pueblo of Picuris"], ["NM"]),
    ("san-ildefonso", "Pueblo of San Ildefonso, New Mexico", ["San Ildefonso Pueblo"], ["NM"]),
    ("santa-ana-pueblo", "Pueblo of Santa Ana, New Mexico", ["Santa Ana Pueblo"], ["NM"]),
    ("zia", "Pueblo of Zia, New Mexico", ["Zia Pueblo"], ["NM"]),
    ("cochiti", "Pueblo of Cochiti, New Mexico", ["Cochiti Pueblo"], ["NM"]),
    ("ysleta-del-sur", "Ysleta del Sur Pueblo of Texas", ["Ysleta del Sur Pueblo", "Tigua"], ["TX"]),
    ("ak-chin", "Ak-Chin Indian Community", [], ["AZ"]),
    ("fort-mcdowell-yavapai", "Fort McDowell Yavapai Nation, Arizona", ["Fort McDowell Yavapai Nation"], ["AZ"]),
    ("yavapai-prescott", "Yavapai-Prescott Indian Tribe", [], ["AZ"]),
    ("tonto-apache", "Tonto Apache Tribe of Arizona", ["Tonto Apache Tribe"], ["AZ"]),
    ("havasupai", "Havasupai Tribe of the Havasupai Reservation, Arizona", ["Havasupai Tribe"], ["AZ"]),
    ("hualapai", "Hualapai Indian Tribe of the Hualapai Indian Reservation, Arizona", ["Hualapai Tribe"], ["AZ"]),
    ("kaibab-paiute", "Kaibab Band of Paiute Indians of the Kaibab Indian Reservation, Arizona", ["Kaibab Band of Paiute Indians"], ["AZ"]),
    ("fort-mojave", "Fort Mojave Indian Tribe of Arizona, California & Nevada", ["Fort Mojave Indian Tribe"], ["AZ", "CA", "NV"]),
    ("cocopah", "Cocopah Tribe of Arizona", ["Cocopah Indian Tribe"], ["AZ"]),
    ("quechan", "Quechan Tribe of the Fort Yuma Indian Reservation, California & Arizona", ["Quechan Tribe"], ["CA", "AZ"]),
    ("te-moak", "Te-Moak Tribe of Western Shoshone Indians of Nevada", ["Te-Moak Tribe of Western Shoshone"], ["NV"]),
    ("duckwater", "Duckwater Shoshone Tribe of the Duckwater Reservation, Nevada", ["Duckwater Shoshone Tribe"], ["NV"]),
    ("ely-shoshone", "Ely Shoshone Tribe of Nevada", ["Ely Shoshone Tribe"], ["NV"]),
    ("walker-river", "Walker River Paiute Tribe of the Walker River Reservation, Nevada", ["Walker River Paiute Tribe"], ["NV"]),
    ("moapa", "Moapa Band of Paiute Indians of the Moapa River Indian Reservation, Nevada", ["Moapa Band of Paiutes"], ["NV"]),
    ("las-vegas-paiute", "Las Vegas Tribe of Paiute Indians of the Las Vegas Indian Colony, Nevada", ["Las Vegas Paiute Tribe"], ["NV"]),
    ("fort-mcdermitt", "Fort McDermitt Paiute and Shoshone Tribes of the Fort McDermitt Indian Reservation, Nevada and Oregon", ["Fort McDermitt Paiute and Shoshone Tribe"], ["NV", "OR"]),
    ("yerington", "Yerington Paiute Tribe of the Yerington Colony & Campbell Ranch, Nevada", ["Yerington Paiute Tribe"], ["NV"]),
    ("duck-valley", "Shoshone-Paiute Tribes of the Duck Valley Reservation, Nevada", ["Shoshone-Paiute Tribes of Duck Valley", "Sho-Pai Tribes"], ["NV", "ID"]),
    ("paiute-utah", "Paiute Indian Tribe of Utah", [], ["UT"]),
    ("nw-shoshone", "Northwestern Band of the Shoshone Nation", ["Northwestern Band of Shoshone Nation"], ["UT", "ID"]),
    ("goshute", "Confederated Tribes of the Goshute Reservation, Nevada and Utah", ["Confederated Tribes of the Goshute Reservation"], ["NV", "UT"]),
    ("kootenai-idaho", "Kootenai Tribe of Idaho", [], ["ID"]),
    ("fort-belknap", "Fort Belknap Indian Community of the Fort Belknap Reservation of Montana", ["Fort Belknap Indian Community"], ["MT"]),
    ("little-shell", "Little Shell Tribe of Chippewa Indians of Montana", [], ["MT"]),
    ("santa-ynez-chumash", "Santa Ynez Band of Chumash Mission Indians of the Santa Ynez Reservation, California", ["Santa Ynez Band of Chumash Mission Indians"], ["CA"]),
    ("viejas", "Viejas (Baron Long) Group of Capitan Grande Band of Mission Indians of the Viejas Reservation, California", ["Viejas Band of Kumeyaay Indians"], ["CA"]),
    ("barona", "Barona Group of Capitan Grande Band of Mission Indians of the Barona Reservation, California", ["Barona Band of Mission Indians"], ["CA"]),
    ("pala", "Pala Band of Mission Indians", [], ["CA"]),
    ("rincon", "Rincon Band of Luiseno Mission Indians of the Rincon Reservation, California", ["Rincon Band of Luiseno Indians"], ["CA"]),
    ("soboba", "Soboba Band of Luiseno Indians, California", ["Soboba Band of Luiseno Indians"], ["CA"]),
    ("cabazon", "Cabazon Band of Cahuilla Indians, California", ["Cabazon Band of Cahuilla Indians", "Cabazon Band of Mission Indians"], ["CA"]),
    ("twenty-nine-palms", "Twenty-Nine Palms Band of Mission Indians of California", ["Twenty-Nine Palms Band of Mission Indians"], ["CA"]),
    ("torres-martinez", "Torres Martinez Desert Cahuilla Indians, California", ["Torres Martinez Desert Cahuilla Indians"], ["CA"]),
    ("chemehuevi", "Chemehuevi Indian Tribe of the Chemehuevi Reservation, California", ["Chemehuevi Indian Tribe"], ["CA"]),
    ("tule-river", "Tule River Indian Tribe of the Tule River Reservation, California", ["Tule River Indian Tribe"], ["CA"]),
    ("table-mountain", "Table Mountain Rancheria", [], ["CA"]),
    ("redding-rancheria", "Redding Rancheria, California", ["Redding Rancheria"], ["CA"]),
    ("susanville", "Susanville Indian Rancheria, California", ["Susanville Indian Rancheria"], ["CA"]),
    ("round-valley", "Round Valley Indian Tribes, Round Valley Reservation, California", ["Round Valley Indian Tribes"], ["CA"]),
    ("big-valley-pomo", "Big Valley Band of Pomo Indians of the Big Valley Rancheria, California", ["Big Valley Band of Pomo Indians"], ["CA"]),
    ("oneida-indian-nation", "Oneida Indian Nation", ["Oneida Indian Nation of New York"], ["NY"]),
    ("cayuga", "Cayuga Nation", [], ["NY"]),
    ("tuscarora", "Tuscarora Nation", [], ["NY"]),
    ("tonawanda-seneca", "Tonawanda Band of Seneca", ["Tonawanda Seneca Nation"], ["NY"]),
    ("onondaga", "Onondaga Nation", [], ["NY"]),
    ("narragansett", "Narragansett Indian Tribe", [], ["RI"]),
    ("mikmaq", "Mi'kmaq Nation", ["Aroostook Band of Micmacs"], ["ME"]),
    ("houlton-maliseet", "Houlton Band of Maliseet Indians", [], ["ME"]),
    ("jena-choctaw", "Jena Band of Choctaw Indians", [], ["LA"]),
    ("iowa-kansas-nebraska", "Iowa Tribe of Kansas and Nebraska", [], ["KS", "NE"]),
    ("sac-fox-missouri", "Sac & Fox Nation of Missouri in Kansas and Nebraska", ["Sac and Fox Nation of Missouri in Kansas and Nebraska"], ["KS", "NE"]),
    ("kickapoo-kansas", "Kickapoo Tribe of Indians of the Kickapoo Reservation in Kansas", ["Kickapoo Tribe in Kansas"], ["KS"]),
    ("flandreau-santee-sioux", "Flandreau Santee Sioux Tribe of South Dakota", ["Flandreau Santee Sioux Tribe"], ["SD"]),
    ("crow-creek-sioux", "Crow Creek Sioux Tribe of the Crow Creek Reservation, South Dakota", ["Crow Creek Sioux Tribe"], ["SD"]),
    ("winnebago-nebraska", "Winnebago Tribe of Nebraska", [], ["NE"]),
    ("kalispel", "Kalispel Indian Community of the Kalispel Reservation", ["Kalispel Tribe of Indians"], ["WA"]),
    ("hoh", "Hoh Indian Tribe", [], ["WA"]),
    ("burns-paiute", "Burns Paiute Tribe", [], ["OR"]),
    ("coos-lower-umpqua-siuslaw", "Confederated Tribes of the Coos, Lower Umpqua and Siuslaw Indians", ["Confederated Tribes of Coos, Lower Umpqua and Siuslaw Indians", "CTCLUSI"], ["OR"]),
    ("sitka-tribe", "Sitka Tribe of Alaska", [], ["AK"]),
    ("ketchikan-indian-community", "Ketchikan Indian Community", ["Ketchikan Indian Corporation"], ["AK"]),
    ("metlakatla", "Metlakatla Indian Community, Annette Island Reserve", ["Metlakatla Indian Community"], ["AK"]),
    ("knik", "Knik Tribe", [], ["AK"]),
    ("chickaloon", "Chickaloon Native Village", [], ["AK"]),
    ("nome-eskimo", "Nome Eskimo Community", [], ["AK"]),
    ("kotzebue", "Native Village of Kotzebue", [], ["AK"]),
    ("craig-tribal-association", "Craig Tribal Association", ["Craig Community Association"], ["AK"]),
    ("native-village-of-barrow", "Native Village of Barrow Inupiat Traditional Government", ["Native Village of Barrow", "Utqiagvik"], ["AK"]),
    ("seldovia", "Seldovia Village Tribe", [], ["AK"]),
    # Phase 3 round 3 (2026-08-28)
    ("cahuilla-band", "Cahuilla Band of Indians", [], ["CA"]),
    ("san-pasqual", "San Pasqual Band of Diegueno Mission Indians of California", ["San Pasqual Band of Mission Indians"], ["CA"]),
    ("mesa-grande", "Mesa Grande Band of Diegueno Mission Indians of the Mesa Grande Reservation, California", ["Mesa Grande Band of Mission Indians"], ["CA"]),
    ("santa-ysabel", "Iipay Nation of Santa Ysabel, California", ["Iipay Nation of Santa Ysabel"], ["CA"]),
    ("jamul", "Jamul Indian Village of California", ["Jamul Indian Village"], ["CA"]),
    ("la-jolla", "La Jolla Band of Luiseno Indians, California", ["La Jolla Band of Luiseno Indians"], ["CA"]),
    ("pauma", "Pauma Band of Luiseno Mission Indians of the Pauma & Yuima Reservation, California", ["Pauma Band of Luiseno Indians"], ["CA"]),
    ("campo", "Campo Band of Diegueno Mission Indians of the Campo Indian Reservation, California", ["Campo Kumeyaay Nation", "Campo Band of Mission Indians"], ["CA"]),
    ("manzanita", "Manzanita Band of Diegueno Mission Indians of the Manzanita Reservation, California", ["Manzanita Band of Kumeyaay Nation"], ["CA"]),
    ("los-coyotes", "Los Coyotes Band of Cahuilla and Cupeno Indians, California", ["Los Coyotes Band of Cahuilla and Cupeno Indians"], ["CA"]),
    ("fort-independence", "Fort Independence Indian Community of Paiute Indians of the Fort Independence Reservation, California", ["Fort Independence Indian Community"], ["CA"]),
    ("big-pine-paiute", "Big Pine Paiute Tribe of the Owens Valley", [], ["CA"]),
    ("lone-pine", "Lone Pine Paiute-Shoshone Tribe", [], ["CA"]),
    ("bridgeport-colony", "Bridgeport Indian Colony", [], ["CA"]),
    ("utu-utu-gwaitu", "Utu Utu Gwaitu Paiute Tribe of the Benton Paiute Reservation, California", ["Utu Utu Gwaitu Paiute Tribe", "Benton Paiute"], ["CA"]),
    ("timbisha", "Timbisha Shoshone Tribe", ["Death Valley Timbisha Shoshone"], ["CA", "NV"]),
    ("graton", "Federated Indians of Graton Rancheria, California", ["Federated Indians of Graton Rancheria"], ["CA"]),
    ("lytton", "Lytton Rancheria of California", [], ["CA"]),
    ("dry-creek", "Dry Creek Rancheria Band of Pomo Indians, California", ["Dry Creek Rancheria Band of Pomo Indians"], ["CA"]),
    ("cloverdale", "Cloverdale Rancheria of Pomo Indians of California", ["Cloverdale Rancheria of Pomo Indians"], ["CA"]),
    ("kashia", "Kashia Band of Pomo Indians of the Stewarts Point Rancheria, California", ["Kashia Band of Pomo Indians"], ["CA"]),
    ("manchester-point-arena", "Manchester Band of Pomo Indians of the Manchester Rancheria, California", ["Manchester-Point Arena Band of Pomo Indians"], ["CA"]),
    ("hopland", "Hopland Band of Pomo Indians, California", ["Hopland Band of Pomo Indians"], ["CA"]),
    ("middletown-rancheria", "Middletown Rancheria of Pomo Indians of California", ["Middletown Rancheria of Pomo Indians"], ["CA"]),
    ("robinson-rancheria", "Robinson Rancheria of Pomo Indians of California", ["Robinson Rancheria"], ["CA"]),
    ("scotts-valley", "Scotts Valley Band of Pomo Indians of California", ["Scotts Valley Band of Pomo Indians"], ["CA"]),
    ("elem", "Elem Indian Colony of Pomo Indians of the Sulphur Bank Rancheria, California", ["Elem Indian Colony"], ["CA"]),
    ("habematolel", "Habematolel Pomo of Upper Lake, California", ["Habematolel Pomo of Upper Lake"], ["CA"]),
    ("koi-nation", "Koi Nation of Northern California", [], ["CA"]),
    ("guidiville", "Guidiville Rancheria of California", ["Guidiville Rancheria"], ["CA"]),
    ("pinoleville", "Pinoleville Pomo Nation, California", ["Pinoleville Pomo Nation"], ["CA"]),
    ("coyote-valley", "Coyote Valley Band of Pomo Indians of California", ["Coyote Valley Band of Pomo Indians"], ["CA"]),
    ("sherwood-valley", "Sherwood Valley Rancheria of Pomo Indians of California", ["Sherwood Valley Rancheria"], ["CA"]),
    ("cahto", "Cahto Tribe of the Laytonville Rancheria", [], ["CA"]),
    ("united-auburn", "United Auburn Indian Community of the Auburn Rancheria of California", ["United Auburn Indian Community"], ["CA"]),
    ("wilton", "Wilton Rancheria, California", ["Wilton Rancheria"], ["CA"]),
    ("shingle-springs", "Shingle Springs Band of Miwok Indians, Shingle Springs Rancheria, California", ["Shingle Springs Band of Miwok Indians"], ["CA"]),
    ("ione", "Ione Band of Miwok Indians of California", ["Ione Band of Miwok Indians"], ["CA"]),
    ("jackson-rancheria", "Jackson Band of Miwuk Indians", ["Jackson Rancheria Band of Miwuk Indians"], ["CA"]),
    ("buena-vista", "Buena Vista Rancheria of Me-Wuk Indians of California", ["Buena Vista Rancheria of Me-Wuk Indians"], ["CA"]),
    ("chicken-ranch", "Chicken Ranch Rancheria of Me-Wuk Indians of California", ["Chicken Ranch Rancheria of Me-Wuk Indians"], ["CA"]),
    ("tuolumne", "Tuolumne Band of Me-Wuk Indians of the Tuolumne Rancheria of California", ["Tuolumne Band of Me-Wuk Indians"], ["CA"]),
    ("mooretown", "Mooretown Rancheria of Maidu Indians of California", ["Mooretown Rancheria of Maidu Indians"], ["CA"]),
    ("berry-creek", "Berry Creek Rancheria of Maidu Indians of California", ["Berry Creek Rancheria of Maidu Indians"], ["CA"]),
    ("enterprise-rancheria", "Enterprise Rancheria of Maidu Indians of California", ["Enterprise Rancheria", "Estom Yumeka Maidu"], ["CA"]),
    ("greenville", "Greenville Rancheria", [], ["CA"]),
    ("lovelock", "Lovelock Paiute Tribe of the Lovelock Indian Colony, Nevada", ["Lovelock Paiute Tribe"], ["NV"]),
    ("winnemucca-colony", "Winnemucca Indian Colony of Nevada", ["Winnemucca Indian Colony"], ["NV"]),
    ("summit-lake", "Summit Lake Paiute Tribe of Nevada", ["Summit Lake Paiute Tribe"], ["NV"]),
    ("skull-valley-goshute", "Skull Valley Band of Goshute Indians of Utah", ["Skull Valley Band of Goshute Indians"], ["UT"]),
    ("san-juan-southern-paiute", "San Juan Southern Paiute Tribe of Arizona", ["San Juan Southern Paiute Tribe"], ["AZ"]),
    ("yakutat", "Yakutat Tlingit Tribe", [], ["AK"]),
    ("hoonah", "Hoonah Indian Association", [], ["AK"]),
    ("wrangell", "Wrangell Cooperative Association", [], ["AK"]),
    ("petersburg-indian-association", "Petersburg Indian Association", [], ["AK"]),
    ("douglas-indian-association", "Douglas Indian Association", [], ["AK"]),
    ("hydaburg", "Hydaburg Cooperative Association", [], ["AK"]),
    ("kasaan", "Organized Village of Kasaan", [], ["AK"]),
    ("kake", "Organized Village of Kake", [], ["AK"]),
    ("angoon", "Angoon Community Association", [], ["AK"]),
    ("chilkoot-haines", "Chilkoot Indian Association (Haines)", ["Chilkoot Indian Association"], ["AK"]),
    ("chilkat-klukwan", "Chilkat Indian Village (Klukwan)", ["Chilkat Indian Village"], ["AK"]),
    ("skagway", "Skagway Village", ["Skagway Traditional Council"], ["AK"]),
    ("sunaq", "Sun'aq Tribe of Kodiak", ["Shoonaq' Tribe of Kodiak"], ["AK"]),
    ("eklutna", "Native Village of Eklutna", [], ["AK"]),
    ("ninilchik", "Ninilchik Village", ["Ninilchik Traditional Council"], ["AK"]),
    ("curyung", "Curyung Tribal Council", ["Native Village of Dillingham"], ["AK"]),
    # Round 4 expansion (2026-08-28): North Slope / NW Arctic
    ("point-hope", "Native Village of Point Hope", [], ["AK"]),
    ("wainwright", "Village of Wainwright", ["Wainwright Traditional Council"], ["AK"]),
    ("nuiqsut", "Native Village of Nuiqsut", [], ["AK"]),
    ("kaktovik", "Kaktovik Village", [], ["AK"]),
    ("atqasuk", "Atqasuk Village", [], ["AK"]),
    ("point-lay", "Native Village of Point Lay", [], ["AK"]),
    ("anaktuvuk-pass", "Village of Anaktuvuk Pass", [], ["AK"]),
    ("selawik", "Native Village of Selawik", [], ["AK"]),
    ("noorvik", "Noorvik Native Community", [], ["AK"]),
    ("kiana", "Native Village of Kiana", [], ["AK"]),
    ("ambler", "Native Village of Ambler", [], ["AK"]),
    ("shungnak", "Native Village of Shungnak", [], ["AK"]),
    ("kobuk", "Native Village of Kobuk", [], ["AK"]),
    ("noatak", "Native Village of Noatak", [], ["AK"]),
    ("kivalina", "Native Village of Kivalina", [], ["AK"]),
    ("buckland", "Native Village of Buckland", [], ["AK"]),
    # Round 4 expansion (2026-08-28): Yukon-Kuskokwim Delta
    ("orutsararmiut", "Orutsararmiut Native Council", ["Orutsararmiut Native Council (Bethel)"], ["AK"]),
    ("akiachak", "Akiachak Native Community", [], ["AK"]),
    ("akiak", "Akiak Native Community", [], ["AK"]),
    ("kwethluk", "Organized Village of Kwethluk", [], ["AK"]),
    ("napaskiak", "Native Village of Napaskiak", [], ["AK"]),
    ("hooper-bay", "Native Village of Hooper Bay", [], ["AK"]),
    ("chevak", "Chevak Native Village", [], ["AK"]),
    ("emmonak", "Emmonak Village", [], ["AK"]),
    ("alakanuk", "Village of Alakanuk", [], ["AK"]),
    ("kotlik", "Village of Kotlik", [], ["AK"]),
    ("algaaciq", "Algaaciq Native Village (St. Mary's)", [], ["AK"]),
    ("asacarsarmiut", "Asa'carsarmiut Tribe", ["Asa'carsarmiut Tribe (Mountain Village)"], ["AK"]),
    ("pilot-station", "Pilot Station Traditional Village", [], ["AK"]),
    ("marshall", "Native Village of Marshall", [], ["AK"]),
    ("kwinhagak", "Native Village of Kwinhagak", ["Native Village of Kwinhagak (Quinhagak)"], ["AK"]),
    ("nunakauyarmiut", "Nunakauyarmiut Tribe", ["Nunakauyarmiut Tribe (Toksook Bay)"], ["AK"]),
    # Round 4 expansion (2026-08-28): Interior Alaska (TCC region)
    ("fort-yukon", "Native Village of Fort Yukon", ["Gwichyaa Zhee"], ["AK"]),
    ("venetie", "Native Village of Venetie Tribal Government", [], ["AK"]),
    ("nenana", "Nenana Native Association", [], ["AK"]),
    ("tanana", "Native Village of Tanana", [], ["AK"]),
    ("louden", "Louden Tribe", ["Louden Tribe (Galena)"], ["AK"]),
    ("nulato", "Nulato Village", [], ["AK"]),
    ("huslia", "Huslia Village", [], ["AK"]),
    ("holy-cross", "Holy Cross Tribe", [], ["AK"]),
    ("anvik", "Anvik Village", [], ["AK"]),
    ("grayling", "Organized Village of Grayling", [], ["AK"]),
    ("shageluk", "Shageluk Native Village", [], ["AK"]),
    ("mcgrath", "McGrath Native Village", [], ["AK"]),
    ("nikolai", "Nikolai Village", ["Edzeno' Village Council"], ["AK"]),
    ("minto", "Native Village of Minto", [], ["AK"]),
    ("northway", "Northway Village", [], ["AK"]),
    ("healy-lake", "Healy Lake Village", [], ["AK"]),
    # Round 4 expansion (2026-08-28): Bristol Bay / Aleutians / Kodiak
    ("new-stuyahok", "New Stuyahok Village", [], ["AK"]),
    ("togiak", "Traditional Village of Togiak", [], ["AK"]),
    ("manokotak", "Manokotak Village", [], ["AK"]),
    ("naknek", "Naknek Native Village", [], ["AK"]),
    ("igiugig", "Igiugig Village", [], ["AK"]),
    ("iliamna", "Village of Iliamna", [], ["AK"]),
    ("newhalen", "Newhalen Village", [], ["AK"]),
    ("nondalton", "Nondalton Village", [], ["AK"]),
    ("ekwok", "Ekwok Village", [], ["AK"]),
    ("aleknagik", "Native Village of Aleknagik", [], ["AK"]),
    ("qawalangin", "Qawalangin Tribe of Unalaska", [], ["AK"]),
    ("agdaagux", "Agdaagux Tribe of King Cove", [], ["AK"]),
    ("qagan-tayagungin", "Qagan Tayagungin Tribe of Sand Point", [], ["AK"]),
    ("old-harbor", "Native Village of Old Harbor", ["Alutiiq Tribe of Old Harbor"], ["AK"]),
    ("ouzinkie", "Native Village of Ouzinkie", [], ["AK"]),
    ("port-lions", "Native Village of Port Lions", [], ["AK"]),
    # Round 4 expansion (2026-08-28): Oklahoma + north-coast California stragglers
    ("kaw-nation", "Kaw Nation, Oklahoma", ["Kaw Nation"], ["OK"]),
    ("ottawa-tribe-oklahoma", "Ottawa Tribe of Oklahoma", [], ["OK"]),
    ("peoria", "Peoria Tribe of Indians of Oklahoma", [], ["OK"]),
    ("modoc-nation", "Modoc Nation", ["Modoc Tribe of Oklahoma"], ["OK"]),
    ("seneca-cayuga", "Seneca-Cayuga Nation", ["Seneca Cayuga Tribe"], ["OK"]),
    ("thlopthlocco", "Thlopthlocco Tribal Town", [], ["OK"]),
    ("kialegee", "Kialegee Tribal Town", [], ["OK"]),
    ("alabama-quassarte", "Alabama-Quassarte Tribal Town", [], ["OK"]),
    ("apache-tribe-oklahoma", "Apache Tribe of Oklahoma", [], ["OK"]),
    ("delaware-tribe", "Delaware Tribe of Indians", [], ["OK"]),
    ("bear-river-rohnerville", "Bear River Band of the Rohnerville Rancheria", [], ["CA"]),
    ("blue-lake-rancheria", "Blue Lake Rancheria", [], ["CA"]),
    ("cher-ae-heights", "Cher-Ae Heights Indian Community of the Trinidad Rancheria", ["Trinidad Rancheria"], ["CA"]),
    ("wiyot", "Wiyot Tribe", [], ["CA"]),
    ("elk-valley", "Elk Valley Rancheria", [], ["CA"]),
    ("quartz-valley", "Quartz Valley Indian Community", [], ["CA"]),
]

# Component reservations of the Minnesota Chippewa Tribe (one BIA entity).
MCT_BANDS = [
    ("leech-lake", "Leech Lake Band of Ojibwe", ["Leech Lake Band"], ["MN"]),
    ("mille-lacs", "Mille Lacs Band of Ojibwe", ["Mille Lacs Band"], ["MN"]),
    ("grand-portage", "Grand Portage Band of Lake Superior Chippewa", ["Grand Portage Band"], ["MN"]),
    ("fond-du-lac", "Fond du Lac Band of Lake Superior Chippewa", ["Fond du Lac Band"], ["MN"]),
    ("bois-forte", "Bois Forte Band of Chippewa", ["Bois Forte Band (Nett Lake)"], ["MN"]),
    ("white-earth", "White Earth Nation", ["White Earth Band"], ["MN"]),
]

NONBIA = [
    ("patawomeck", "Patawomeck Indian Tribe of Virginia", [], ["VA"],
     "state_recognized",
     "Virginia state-recognized; not on the BIA list of federally recognized tribes."),
    ("chappaquiddick-wampanoag", "Chappaquiddick Wampanoag Tribe", ["Chappaquiddick Tribe of the Wampanoag Nation"], ["MA"],
     "unrecognized",
     "Not on the BIA list; no federal recognition. Registry references it via the WAMP Owned directory (TBD-013)."),
]

# nation_source string in sources.jsonl -> nation_id list.
# Sources absent from this map get nation_ids [] with a non-single scope from
# SCOPE_OVERRIDES (org/agency/ANC rows have no nation identity of their own).
NATION_SOURCE_MAP = {
    "Tulalip Tribes": ["bia:tulalip-tribes"],
    "Muscogee (Creek) Nation": ["bia:muscogee-creek-nation"],
    "Fallon Paiute-Shoshone Tribe": ["bia:fallon-paiute-shoshone"],
    "Mechoopda Indian Tribe of Chico Rancheria": ["bia:mechoopda"],
    "Patawomeck Indian Tribe of Virginia": ["nonbia:patawomeck"],
    "Wampanoag Tribe of Gay Head (Aquinnah)": ["bia:wampanoag-aquinnah"],
    "Kenaitze Indian Tribe": ["bia:kenaitze"],
    "Pamunkey Indian Tribe": ["bia:pamunkey"],
    "Forest County Potawatomi Community": ["bia:forest-county-potawatomi"],
    "Nez Perce Tribe": ["bia:nez-perce"],
    "Chickasaw Nation": ["bia:chickasaw-nation"],
    "Confederated Tribes of Grand Ronde": ["bia:grand-ronde"],
    "Mandan, Hidatsa and Arikara Nation": ["bia:three-affiliated-tribes"],
    "Standing Rock Sioux Tribe": ["bia:standing-rock-sioux"],
    "Muckleshoot Indian Tribe": ["bia:muckleshoot"],
    "Salt River Pima-Maricopa Indian Community": ["bia:salt-river-pima-maricopa"],
    "Oneida Nation": ["bia:oneida-nation-wi"],
    "Confederated Tribes of the Umatilla Indian Reservation": ["bia:umatilla"],
    "Confederated Tribes of Warm Springs": ["bia:warm-springs"],
    "Puyallup Tribe of Indians": ["bia:puyallup"],
    "Blackfeet Nation": ["bia:blackfeet"],
    "Poarch Band of Creek Indians": ["bia:poarch-band"],
    "Confederated Salish and Kootenai Tribes": ["bia:salish-kootenai"],
    "Navajo Nation": ["bia:navajo-nation"],
    "Cherokee Nation": ["bia:cherokee-nation"],
    "Confederated Tribes of the Colville Reservation": ["bia:colville"],
    "Spokane Tribe of Indians": ["bia:spokane"],
    "Southern Ute Indian Tribe": ["bia:southern-ute"],
    "Rosebud Sioux Tribe": ["bia:rosebud-sioux"],
    "Yurok Tribe": ["bia:yurok"],
    "Ute Indian Tribe of the Uintah and Ouray Reservation": ["bia:ute-indian-tribe"],
    "Sault Ste. Marie Tribe of Chippewa Indians": ["bia:sault-ste-marie"],
    "Eastern Band of Cherokee Indians": ["bia:eastern-band-cherokee"],
    "Tohono O’odham Nation": ["bia:tohono-oodham"],
    "Choctaw Nation of Oklahoma": ["bia:choctaw-nation-oklahoma"],
    "Pawnee Nation of Oklahoma": ["bia:pawnee-nation"],
    "Otoe-Missouria Tribe": ["bia:otoe-missouria"],
    "Leech Lake Band of Ojibwe": ["bia:minnesota-chippewa-tribe--leech-lake"],
    "Lummi Nation": ["bia:lummi"],
    "Coeur d’Alene Tribe": ["bia:coeur-dalene"],
    "Shoshone-Bannock Tribes": ["bia:shoshone-bannock"],
    "Sisseton Wahpeton Oyate": ["bia:sisseton-wahpeton-oyate"],
    "Mississippi Band of Choctaw Indians": ["bia:mississippi-choctaw"],
    "Pyramid Lake Paiute Tribe": ["bia:pyramid-lake-paiute"],
    "Red Cliff Band of Lake Superior Chippewa": ["bia:red-cliff-chippewa"],
    "Bad River Band of Lake Superior Chippewa": ["bia:bad-river-chippewa"],
    "WAMP Owned / Chappaquiddick Wampanoag": ["nonbia:chappaquiddick-wampanoag"],
    "Cheyenne River Sioux Tribe / Four Bands Community Fund": ["bia:cheyenne-river-sioux"],
    "Menominee Indian Tribe of Wisconsin": ["bia:menominee"],
    "Osage Nation community / Osage News": ["bia:osage-nation"],
    "Citizen Potawatomi Nation": ["bia:citizen-potawatomi"],
    "Catawba Nation": ["bia:catawba"],
    "Keweenaw Bay Indian Community": ["bia:keweenaw-bay"],
    "Native Village of Eyak": ["bia:native-village-of-eyak"],
    "Snoqualmie Indian Tribe": ["bia:snoqualmie"],
    "Penobscot Nation": ["bia:penobscot"],
    "Grand Traverse Band of Ottawa and Chippewa Indians": ["bia:grand-traverse-band"],
    "Mille Lacs Band of Ojibwe": ["bia:minnesota-chippewa-tribe--mille-lacs"],
    "Little Traverse Bay Bands of Odawa Indians": ["bia:little-traverse-bay-bands"],
    "Cowlitz Indian Tribe": ["bia:cowlitz"],
    "Grand Portage Band of Lake Superior Chippewa": ["bia:minnesota-chippewa-tribe--grand-portage"],
    "Tolowa Dee-ni’ Nation": ["bia:tolowa-dee-ni"],
    "Hoopa Valley Tribe": ["bia:hoopa-valley"],
    "Bishop Paiute Tribe": ["bia:bishop-paiute"],
    "Mashantucket Pequot Tribal Nation": ["bia:mashantucket-pequot"],
    "Quinault Indian Nation": ["bia:quinault"],
    "Yakama Nation": ["bia:yakama"],
    "Yavapai-Apache Nation": ["bia:yavapai-apache"],
    "Spirit Lake Nation": ["bia:spirit-lake"],
    "Northern Cheyenne Tribe": ["bia:northern-cheyenne"],
    "Assiniboine and Sioux Tribes of the Fort Peck Indian Reservation": ["bia:fort-peck"],
    "Eastern Shoshone Tribe and Northern Arapaho Tribe / Wind River": ["bia:eastern-shoshone", "bia:northern-arapaho"],
    "Karuk Tribe": ["bia:karuk"],
    "Ute Mountain Ute Tribe": ["bia:ute-mountain-ute"],
    "Klamath Tribes": ["bia:klamath"],
    "Oglala Sioux Tribe": ["bia:oglala-sioux"],
    "Chippewa Cree Tribe of the Rocky Boy’s Reservation": ["bia:chippewa-cree"],
    "Seminole Nation of Oklahoma": ["bia:seminole-nation-oklahoma"],
    "Kiowa Tribe": ["bia:kiowa"],
    "Comanche Nation": ["bia:comanche"],
    "Cheyenne and Arapaho Tribes": ["bia:cheyenne-and-arapaho"],
    "Wichita and Affiliated Tribes": ["bia:wichita-affiliated"],
    "Swinomish Indian Tribal Community": ["bia:swinomish"],
    "Red Lake Nation": ["bia:red-lake"],
    "White Earth Nation": ["bia:minnesota-chippewa-tribe--white-earth"],
    "Mashpee Wampanoag Tribe": ["bia:mashpee-wampanoag"],
    "Lumbee Tribe of North Carolina": ["bia:lumbee"],
    "Omaha Tribe of Nebraska": ["bia:omaha-tribe"],
    "Crow Tribe of Indians": ["bia:crow-tribe"],
    "San Carlos Apache Tribe": ["bia:san-carlos-apache"],
    "Central Council of the Tlingit and Haida Indian Tribes of Alaska": ["bia:tlingit-haida"],
    "Colorado River Indian Tribes": ["bia:colorado-river-indian-tribes"],
    "Pueblo of Laguna": ["bia:pueblo-of-laguna"],
    "Fond du Lac Band of Lake Superior Chippewa": ["bia:minnesota-chippewa-tribe--fond-du-lac"],
    "Bois Forte Band of Chippewa": ["bia:minnesota-chippewa-tribe--bois-forte"],
    "Prairie Island Indian Community": ["bia:prairie-island"],
    "Saint Regis Mohawk Tribe": ["bia:saint-regis-mohawk"],
    "Ho-Chunk Nation": ["bia:ho-chunk"],
    "Quapaw Nation": ["bia:quapaw"],
    "Sault Tribe Business Alliance": ["bia:sault-ste-marie"],
    "Menominee Indian Tribe community / Menominee Chamber of Commerce": ["bia:menominee"],
    "South Puget Intertribal Planning Agency": [
        "bia:chehalis", "bia:nisqually", "bia:shoalwater-bay", "bia:skokomish", "bia:squaxin-island",
    ],
    "Squaxin Island Tribe": ["bia:squaxin-island"],
    "Gila River Indian Community": ["bia:gila-river"],
    "Pascua Yaqui Tribe": ["bia:pascua-yaqui"],
    "Turtle Mountain Band of Chippewa Indians": ["bia:turtle-mountain-chippewa"],
    "Osage Nation": ["bia:osage-nation"],
    # Wave 5.1 Phase 3 expansion sources
    "Confederated Tribes of Siletz Indians": ["bia:siletz"],
    "Nisqually Indian Tribe": ["bia:nisqually"],
    "Pokagon Band of Potawatomi Indians": ["bia:pokagon-band"],
    "Pueblo of Jemez": ["bia:jemez"],
    "Pueblo of Pojoaque": ["bia:pojoaque"],
    "Pueblo of San Felipe": ["bia:san-felipe"],
    "Confederated Tribes of the Chehalis Reservation": ["bia:chehalis"],
    # Phase 3 round 2 sources
    "Fort Belknap Indian Community": ["bia:fort-belknap"],
    "Houlton Band of Maliseet Indians": ["bia:houlton-maliseet"],
    "Shoshone-Paiute Tribes of the Duck Valley Reservation": ["bia:duck-valley"],
    # Phase 3 round 3 sources
    "Hoonah Indian Association": ["bia:hoonah"],
}

# source_id -> nation_scope for rows whose scope is not implied by the map
# (multi-tribe intertribal agencies stay multi_nation via the map).
SCOPE_OVERRIDES = {
    # National organizations / federal programs
    "TBD-063": "national",  # U.S. Indian Arts and Crafts Board
    "TBD-065": "national",  # Minneapolis Fed CICD
    "TBD-066": "national",  # BIA Buy Indian
    "TBD-069": "national",  # American Indigenous Business Leaders
    "TBD-070": "national",  # First Peoples Fund
    "TBD-072": "national",  # BIA Tribal Leaders Directory
    "TBD-163": "national",  # Council for Tribal Employment Rights
    # Regional / state agencies, chambers, ANCs
    "TBD-064": "regional",  # USET
    "TBD-067": "regional",  # Washington Native Business Center
    "TBD-068": "regional",  # Texas Native Health
    "TBD-071": "regional",  # Washington Native American Chamber of Commerce
    "TBD-125": "regional",  # Bristol Bay Native Corporation
    "TBD-126": "regional",  # Ahtna, Inc.
    "TBD-127": "regional",  # Chugach Alaska Corporation
    "TBD-128": "regional",  # Afognak Native Corporation
    "TBD-129": "regional",  # Koniag, Inc.
    "TBD-130": "regional",  # Calista Corporation
    "TBD-131": "regional",  # Bering Straits Native Corporation
    "TBD-143": "regional",  # MnDOT
    "TBD-144": "regional",  # SDDOT
    "TBD-145": "regional",  # Minnesota OSP
    "TBD-146": "regional",  # Minnesota American Indian Chamber of Commerce
    "TBD-147": "regional",  # NACDI
    "TBD-148": "regional",  # Minnesota Indigenous Business Alliance
    "TBD-149": "regional",  # Wisconsin & Midwest Native Entrepreneurs Directory
    "TBD-150": "regional",  # AICC of New Mexico
    "TBD-151": "regional",  # Northwest Native Chamber
    "TBD-152": "regional",  # AICC of Arizona
    "TBD-153": "regional",  # AICC of Oklahoma
    "TBD-154": "regional",  # Rocky Mountain Indian Chamber of Commerce
    "TBD-155": "regional",  # Montana Department of Commerce
    "TBD-156": "regional",  # Colorado Proud
    "TBD-161": "regional",  # AICC of California
    "TBD-162": "regional",  # Washington OMWBE
    "TBD-164": "regional",  # Oklahoma Department of Commerce TERO enumeration
    "TBD-165": "regional",  # ANVCA
    "TBD-176": "regional",  # Kawerak Bering Strait Business Directory (20-tribe consortium region)
    "TBD-178": "regional",  # TCC TERO vendor listing (42-village Interior Alaska consortium region)
}


def nation_rows() -> list[dict]:
    rows = []
    for slug, bia_name, variants, states in BIA:
        names = [bia_name] + [v for v in variants if v != bia_name]
        rows.append({
            "nation_id": f"bia:{slug}",
            "bia_name": bia_name,
            "names": names,
            "states": states,
            "on_bia_list": True,
            "recognition": "federal",
            "parent_nation_id": None,
            "bia_list_edition": "2026-01-30 Federal Register notice (575 entities)",
            "name_verified_against_list": False,
            "notes": None,
        })
    for slug, name, variants, states in MCT_BANDS:
        rows.append({
            "nation_id": f"bia:minnesota-chippewa-tribe--{slug}",
            "bia_name": None,
            "names": [name] + variants,
            "states": states,
            "on_bia_list": False,
            "recognition": "federal",
            "parent_nation_id": "bia:minnesota-chippewa-tribe",
            "bia_list_edition": "2026-01-30 Federal Register notice (575 entities)",
            "name_verified_against_list": False,
            "notes": "Component reservation of the Minnesota Chippewa Tribe — one "
                     "BIA-listed entity; Cedar keys bands separately because sources do.",
        })
    for slug, name, variants, states, recognition, note in NONBIA:
        rows.append({
            "nation_id": f"nonbia:{slug}",
            "bia_name": None,
            "names": [name] + variants,
            "states": states,
            "on_bia_list": False,
            "recognition": recognition,
            "parent_nation_id": None,
            "bia_list_edition": "2026-01-30 Federal Register notice (575 entities)",
            "name_verified_against_list": False,
            "notes": note,
        })
    return rows


def main() -> None:
    nations = nation_rows()
    with (ROOT / "nations.jsonl").open("w") as f:
        for row in nations:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    known = {n["nation_id"] for n in nations}
    src_path = ROOT / "sources.jsonl"

    # First pass: a tribal nation_source with neither a map entry nor an
    # explicit scope override means the map is out of date (new or renamed
    # source row). Fail before writing rather than silently downgrading an
    # existing mapping to nation_ids: [] / nation_scope: unknown.
    src_rows = [json.loads(line) for line in src_path.read_text().splitlines()]
    unmapped_tribal = [
        (s["source_id"], s["nation_source"])
        for s in src_rows
        if s["nation_source"] not in NATION_SOURCE_MAP
        and s["source_id"] not in SCOPE_OVERRIDES
    ]
    if unmapped_tribal:
        print("FAIL: unmapped nation_source rows (add to NATION_SOURCE_MAP or "
              "SCOPE_OVERRIDES before regenerating):", file=sys.stderr)
        for sid, ns in unmapped_tribal:
            print(f"  {sid}: {ns}", file=sys.stderr)
        raise SystemExit(1)

    out_lines = []
    for s in src_rows:
        ids = NATION_SOURCE_MAP.get(s["nation_source"])
        override = SCOPE_OVERRIDES.get(s["source_id"])
        if ids:
            assert all(i in known for i in ids), (s["source_id"], ids)
            scope = override or ("multi_nation" if len(ids) > 1 else "single_nation")
        else:
            ids = []
            scope = override
        rebuilt = {}
        for k, v in s.items():
            rebuilt[k] = v
            if k == "country":
                rebuilt["nation_ids"] = ids
                rebuilt["nation_scope"] = scope
        # rows that already carried the keys (idempotent re-run)
        rebuilt["nation_ids"] = ids
        rebuilt["nation_scope"] = scope
        out_lines.append(json.dumps(rebuilt, ensure_ascii=False))
    src_path.write_text("\n".join(out_lines) + "\n")

    print(f"nations.jsonl: {len(nations)} rows")


if __name__ == "__main__":
    main()
