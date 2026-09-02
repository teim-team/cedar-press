
**Note: for schools and colleges, I assign them to tribes if they are tribally owned and / or operated. I drop them if they are public schools even if they are located entirely on a reservation. I also drop schools & colleges jointly controlled by multiple tribes or serving multiple tribes / reservations (although all tribal colleges accept members of all tribes, some serve primarily a single tribe - I assign them to that tribe in that case; those that don't primarily serve a single tribe are not assigned to any tribe). It is possible to further drop schools that are BIA-operated but not tribally controlled (there are few of those in this data.) There are 58 Bureau-Operated Schools and 129 Tribally-Controlled Schools. I currently keep both types but need to drop BIA-Operated schools.

import delimited "C:\Users\Anna Malinovskaya\Desktop\Data on tribes and reservations\Assistance_PrimeTransactions_2023-04-09_H19M53S53_1.csv", bindquote(strict) stripquote(no) maxquotedrows(1000) clear

gen Tribe = strlower(recipient_name)
gen recipient_name_orig = Tribe

drop if recipient_state_code=="AK"

gen tribe_id = .

replace Tribe = subinstr(Tribe, `"""',  "", .)

gen flag = 0

replace tribe_id=1 if strpos(Tribe,"absentee")==1
tab Tribe if tribe_id==1
replace tribe_id=2 if strpos(Tribe, "agua")==1
tab Tribe if tribe_id==2
replace flag=1 if Tribe=="agua caliente solar, llc"
**this enterprise appears to have no connection to the tribe
replace tribe_id=3 if strpos(Tribe, "ak-chin")==1
replace tribe_id=3 if strpos(Tribe, "ak chin")==1
tab Tribe if tribe_id==3
*ak-chin farms is a tribal enterprise
replace tribe_id=4 if strpos(Tribe, "alabama-coushatta")==1
replace tribe_id=4 if strpos(Tribe, "alabama coushatta tribe of texas")==1
replace tribe_id=4 if strpos(Tribe, "alabama-couchatta")==1
replace tribe_id=4 if strpos(Tribe, "alabama coushatta indian")==1
replace tribe_id=4 if strpos(Tribe, "hsg auth alabama coushatta")==1
tab Tribe if tribe_id==4
replace tribe_id=5 if strpos(Tribe, "alabama-quassarte")==1
replace tribe_id=5 if strpos(Tribe, "alabama quassarte")==1
tab Tribe if tribe_id==5
**alabama quassarte service association is a tribal enterprise
replace tribe_id=6 if strpos(Tribe, "alturas")==1
tab Tribe if tribe_id==6
replace flag=1 if Tribe=="alturas fire department"
replace tribe_id=7 if strpos(Tribe, "apache")==1
tab Tribe if tribe_id==7

replace tribe_id=8 if strpos(Tribe, "assiniboine")==1
replace tribe_id=8 if strpos(Tribe, "fort peck")==1
replace tribe_id=8 if strpos(Tribe, "ft. peck assiniboine & sioux tribes")==1
tab Tribe if tribe_id==8
replace tribe_id=9 if strpos(Tribe, "augustine")==1
tab Tribe if tribe_id==9

replace tribe_id=10 if strpos(Tribe, "bad river")==1
tab Tribe if tribe_id==10
replace tribe_id=13 if strpos(Tribe, "bay mills")==1
tab Tribe if tribe_id==13
replace tribe_id=14 if strpos(Tribe, "rohnerville")==1
replace tribe_id=14 if strpos(Tribe, "the rohnerville rancheria")==1
replace tribe_id=14 if strpos(Tribe, "bear river")==1
tab Tribe if tribe_id==14
replace tribe_id=15 if strpos(Tribe, "berry creek")==1
tab Tribe if tribe_id==15

replace tribe_id=17 if strpos(Tribe, "big lagoon")==1
tab Tribe if tribe_id==17
replace tribe_id=18 if strpos(Tribe, "big pine")==1
tab Tribe if tribe_id==18
replace tribe_id=19 if strpos(Tribe, "big sandy")==1
tab Tribe if tribe_id==19
replace tribe_id=20 if strpos(Tribe, "big valley")==1
tab Tribe if tribe_id==20
replace tribe_id=21 if strpos(Tribe, "bishop")==1
tab Tribe if tribe_id==21

replace tribe_id=22 if strpos(Tribe, "blackfeet")==1
replace tribe_id=22 if strpos(Tribe, "the blackfeet tribe")==1
replace tribe_id=22 if strpos(Tribe, "black feet tribe, the")==1
tab Tribe if tribe_id==22
replace flag=1 if Tribe=="blackfeet oil & gas"
replace tribe_id=23 if strpos(Tribe, "blue lake")==1
tab Tribe if tribe_id==23
replace tribe_id=24 if strpos(Tribe, "bois")==1
tab Tribe if tribe_id==24
replace flag=1 if Tribe=="boise city ada housing authority"
replace tribe_id=25 if strpos(Tribe, "bridgeport")==1
tab Tribe if tribe_id==25
replace tribe_id=26 if strpos(Tribe, "buena vista")==1
replace tribe_id=26 if strpos(Tribe, "the buena vista rancheria of the me-wuk indians")==1
tab Tribe if tribe_id==26
replace flag=1 if Tribe=="buena vista, city of"
replace tribe_id=27 if strpos(Tribe, "burns paiute tribe")==1
tab Tribe if tribe_id==27

replace tribe_id=28 if strpos(Tribe, "cabazon")==1
tab Tribe if tribe_id==28
replace tribe_id=29 if strpos(Tribe, "colusa")==1
replace tribe_id=29 if strpos(Tribe, "cachil")==1
tab Tribe if tribe_id==29
replace tribe_id=30 if strpos(Tribe, "caddo")==1
replace tribe_id=30 if strpos(Tribe, "delaware nation")==1 & recipient_city_name=="CADDO-WICHITA-DELAWAR"
replace tribe_id=30 if strpos(Tribe, "wichita & affiliated tribes")==1 & recipient_city_name=="CADDO-WICHITA-DELAWAR" 
tab Tribe if tribe_id==30
replace tribe_id=31 if strpos(Tribe, "laytonville")==1
replace tribe_id=31 if strpos(Tribe, "cahto")==1
tab Tribe if tribe_id==31

replace tribe_id=32 if strpos(Tribe, "cahuilla")==1
tab Tribe if tribe_id==32
replace tribe_id=33 if strpos(Tribe, "california valley")==1 
replace tribe_id=33 if strpos(Tribe, "sheep")==1 
tab Tribe if tribe_id==33
**California Valley is missing data! "They were previously known as the Sheep Ranch Rancheria or the Sheep Ranch Rancheria of Me-Wuk Indian of California" (wiki)
replace tribe_id=34 if strpos(Tribe, "campo")==1
tab Tribe if tribe_id==34
replace tribe_id=35 if strpos(Tribe, "capitan grande")==1
replace tribe_id=35 if strpos(Tribe, "barona")==1
tab Tribe if tribe_id==35

replace tribe_id=36 if strpos(Tribe, "carson colony")==1
**note: Carson Colony is missing data!
replace tribe_id=37 if strpos(Tribe, "catawba")==1
replace tribe_id=37 if strpos(Tribe, "iswa development corporation")==1
tab Tribe if tribe_id==37
replace tribe_id=38 if strpos(Tribe, "cayuga")==1
tab Tribe if tribe_id==38
replace tribe_id=39 if strpos(Tribe, "cedar band")==1
**note: Cedar Band of Paiutes is missing data but perhaps they are combined with Utah Paiutes in the data 

replace tribe_id=40 if strpos(Tribe, "cedarville rancheria")==1
tab Tribe if tribe_id==40
replace tribe_id=41 if strpos(Tribe, "chemehuevi")==1
tab Tribe if tribe_id==41
replace tribe_id=42 if strpos(Tribe, "cher-")==1
replace tribe_id=42 if strpos(Tribe, "trinidad")==1
tab Tribe if tribe_id==42

replace tribe_id=43 if strpos(Tribe, "cherokee")==1
replace tribe_id=43 if strpos(Tribe, "the cherokee nation")==1
tab Tribe if tribe_id==43
replace tribe_id=44 if strpos(Tribe, "cheyenne-arapaho")==1
replace tribe_id=44 if strpos(Tribe, "cheyenne and arapaho")==1
replace tribe_id=44 if strpos(Tribe, "cheyenne & arapaho")==1
replace tribe_id=44 if strpos(Tribe, "cheyenne arapaho tribe")==1
replace tribe_id=44 if Tribe=="southern cheyenne arapahoe tribes of oklahoma"
tab Tribe if tribe_id==44
replace tribe_id=45 if strpos(Tribe, "cheyenne river")==1
tab Tribe if tribe_id==45
replace flag=1 if Tribe=="cheyenne river alcohol & drug abuse committee"
replace tribe_id=46 if strpos(Tribe, "chickahominy")==1
tab Tribe if tribe_id==46
replace tribe_id=47 if strpos(Tribe, "chickahominy indian tribe - eastern")==1
tab Tribe if tribe_id==47
replace tribe_id=48 if strpos(Tribe, "chicken")==1
tab Tribe if tribe_id==48

replace tribe_id=49 if strpos(Tribe, "chippewa cree")==1
replace tribe_id=49 if strpos(Tribe, "the chippewa cree tribe")==1
replace tribe_id=49 if strpos(Tribe, "rocky boy")==1
tab Tribe if tribe_id==49
replace flag=1 if Tribe=="chippewa cree const corp" | Tribe=="chippewa cree construction corp" 
**rocky boy schools and chippewa cree tribe/health care are not flagged because they are affiliated with the tribe
replace tribe_id=50 if strpos(Tribe, "chitimacha")==1
tab Tribe if tribe_id==50
replace tribe_id=51 if strpos(Tribe, "citizen")==1
tab Tribe if tribe_id==51
replace flag=1 if Tribe==" citizens fire company #2" | Tribe=="citizens reinvesting in shaw"
replace tribe_id=52 if strpos(Tribe, "cloverdale")==1
tab Tribe if tribe_id==52
replace tribe_id=53 if strpos(Tribe, "cocopah")==1
tab Tribe if tribe_id==53
replace tribe_id=54 if strpos(Tribe, "coeur")==1
replace tribe_id=54 if strpos(Tribe, "the coeur d'alene tribe")==1
replace tribe_id=54 if strpos(Tribe, "couer d'alene tribe")==1
tab Tribe if tribe_id==54

replace tribe_id=55 if strpos(Tribe, "cold springs")==1
tab Tribe if tribe_id==55
replace tribe_id=56 if strpos(Tribe, "colorado river")==1
tab Tribe if tribe_id==56
**keep colorado river residential management corporation, it recieved funding for the tribe 
replace tribe_id=57 if strpos(Tribe, "comanche")==1
tab Tribe if tribe_id==57
replace flag=1 if Tribe=="comanche, city of" | Tribe=="comanche" | Tribe=="comanche county consolidated hospital district"
replace tribe_id=58 if strpos(Tribe, "salish")==1
replace tribe_id=58 if strpos(Tribe, "confederated salish and kootenai tribes")==1
replace tribe_id=58 if strpos(Tribe, "conf salish kootenai tribe")==1
replace tribe_id=58 if strpos(Tribe, "confederated salish &")==1
replace tribe_id=58 if strpos(Tribe, "confederated salish and")==1
tab Tribe if tribe_id==58
replace tribe_id=59 if strpos(Tribe, "yakama")==1
replace tribe_id=59 if strpos(Tribe, "confederated tribes and bands of the yakama nation, the")==1
replace tribe_id=59 if strpos(Tribe, "confederated tribes and bands of the yukama n")==1
replace tribe_id=59 if strpos(Tribe, "tribes and bands of the yakama nation")==1
replace tribe_id=59 if strpos(Tribe, "yakima")==1
replace tribe_id=59 if strpos(Tribe, "conf trbs&bds of yakima ind na")==1
replace tribe_id=59 if strpos(Tribe, "confederated tribes & bands of the yakima")==1
replace tribe_id=59 if strpos(Tribe, "confederated tribes & bands of yakama nation")==1
replace tribe_id=59 if strpos(Tribe, "confederated tribes and bands of the yakama n")==1
replace tribe_id=59 if Tribe=="confederated tribes & bands of"==1
replace tribe_id=59 if Tribe=="confederated tribes and"==1
replace tribe_id=59 if Tribe=="confederated tribes"==1
**note: I assined the last one based on primary city of performance
tab Tribe if tribe_id==59

replace tribe_id=60 if strpos(Tribe, "siletz")==1
replace tribe_id=60 if strpos(Tribe, "confederated tribes of siletz indians of oregon")==1
replace tribe_id=60 if strpos(Tribe, "confederated tribes of the siletz indians")==1
replace tribe_id=60 if strpos(Tribe, "confederated tribes of siletz")==1
tab Tribe if tribe_id==60
replace tribe_id=61 if strpos(Tribe, "chehalis")==1
replace tribe_id=61 if strpos(Tribe, "confederated tribes of the chehalis reservation")==1
replace tribe_id=61 if strpos(Tribe, "confederated tribes of the chehalis reservati")==1
tab Tribe if tribe_id==61
replace tribe_id=62 if strpos(Tribe, "colville")==1
replace tribe_id=62 if strpos(Tribe, "confederated tribes of the colville reservation, the")==1
replace tribe_id=62 if strpos(Tribe, "confederated tribes of the colville reservati")==1
replace tribe_id=62 if strpos(Tribe, "confederate tribes of the colville reservatio")==1
replace tribe_id=62 if strpos(Tribe, "confederated tribes of the col")==1
replace tribe_id=62 if strpos(Tribe, "confederated tribes of col")==1
tab Tribe if tribe_id==62

replace tribe_id=63 if strpos(Tribe, "coos")==1
replace tribe_id=63 if strpos(Tribe, "confederated tribes of coos, lower umpqua and siuslaw indian")==1
replace tribe_id=63 if strpos(Tribe, "conf trbs of coos lower umpqua")==1
replace tribe_id=63 if strpos(Tribe, "confederated tribes of coos, lower umpqua & s")==1
tab Tribe if tribe_id==63
replace flag=1 if Tribe=="coos county family health services"
replace tribe_id=64 if strpos(Tribe, "goshute")==1
replace tribe_id=64 if strpos(Tribe, "confederated tribes of the goshute reservation")==1
replace tribe_id=64 if strpos(Tribe, "conf tribes of the goshute")==1
replace tribe_id=64 if strpos(Tribe, "confederated tribe goshute res")==1
tab Tribe if tribe_id==64

replace tribe_id=65 if strpos(Tribe, "grand ronde")==1
replace tribe_id=65 if strpos(Tribe, "the confederated tribes of the grand ronde co")==1
replace tribe_id=65 if strpos(Tribe, "confederated tribes of the grand ronde community of oregon")==1
replace tribe_id=65 if strpos(Tribe, "confederated tribes of grand ronde community")==1
replace tribe_id=65 if strpos(Tribe, "confederated tribes of grand")==1
tab Tribe if tribe_id==65
replace tribe_id=66 if strpos(Tribe, "umatilla")==1
replace tribe_id=66 if strpos(Tribe, "confederated tribes of the umatilla indian reservation")==1
replace tribe_id=66 if strpos(Tribe, "conf tribe-umatilla indian")==1
replace tribe_id=66 if strpos(Tribe, "confederate tribe of the umatilla indian rese")==1
replace tribe_id=66 if strpos(Tribe, "confederated tribes of the uma")==1
replace tribe_id=66 if strpos(Tribe, "confederated tribes of umatilla indian reserv")==1
replace tribe_id=66 if strpos(Tribe, "conf trbs umatilla ind reserva")==1
replace tribe_id=66 if strpos(Tribe, "confederated trives of the umatilla")==1
tab Tribe if tribe_id==66
replace tribe_id=67 if strpos(Tribe, "warm")==1
replace tribe_id=67 if strpos(Tribe, "conf tribes of warm springs")==1
replace tribe_id=67 if strpos(Tribe, "confed tribes warm springs")==1
replace tribe_id=67 if strpos(Tribe, "confederated tribes of warm springs reservation of oregon")==1
replace tribe_id=67 if strpos(Tribe, "the confederated tribes of warm springs reser")==1
replace tribe_id=67 if strpos(Tribe, "confederated tribes of  the warms springs res")==1
replace tribe_id=67 if strpos(Tribe, "confederated tribes of the warm springs india")==1
replace tribe_id=67 if strpos(Tribe, "confederated tribes of the warm springs reser")==1
replace tribe_id=67 if strpos(Tribe, "confederated tribes of warm springs")==1
tab Tribe if tribe_id==67
**warm springs geo visions and warm springs telecommunications company are tribal enterprises; 
replace flag=1 if Tribe=="warm springs community action team" | Tribe=="warm springs health & wellness center" 
replace tribe_id=68 if strpos(Tribe, "coquille")==1
tab Tribe if tribe_id==68

replace tribe_id=69 if strpos(Tribe, "coushatta tribe of lou")==1
tab Tribe if tribe_id==69
replace tribe_id=70 if strpos(Tribe, "cow creek")==1
tab Tribe if tribe_id==70
replace tribe_id=71 if strpos(Tribe, "cowlitz")==1
tab Tribe if tribe_id==71
**cowlitz community foundation seems to belong to the tribe
replace tribe_id=72 if strpos(Tribe, "coyote valley")==1
tab Tribe if tribe_id==72
replace tribe_id=73 if strpos(Tribe, "crow creek")==1
tab Tribe if tribe_id==73
replace tribe_id=74 if strpos(Tribe, "crow tribe")==1
replace tribe_id=74 if strpos(Tribe, "apsaalooke")==1 
replace tribe_id=74 if strpos(Tribe, "crow indian tribe social service division")==1 
replace tribe_id=74 if strpos(Tribe, "crow tribal")==1 
tab Tribe if tribe_id==74
replace tribe_id=75 if strpos(Tribe, "delaware tribe of western oklahoma")==1
replace tribe_id=75 if strpos(Tribe, "delaware tribe of w. oklahoma")==1
replace tribe_id=75 if strpos(Tribe, "delaware nation")==1 & recipient_city_name!="CADDO-WICHITA-DELAWAR"
replace tribe_id=75 if strpos(Tribe, "the delaware nation")==1 
replace tribe_id=75 if strpos(Tribe, "delaware tribe of indians")==1 & recipient_city_name=="ANADARKO"
tab Tribe if tribe_id==75
replace tribe_id=76 if strpos(Tribe, "delaware tribe of indians")==1 & recipient_city_name!="ANADARKO"
replace tribe_id=76 if strpos(Tribe, "delaware tribe")==1 & recipient_city_name=="BARTLESVILLE"
replace tribe_id=76 if strpos(Tribe, "delaware tribe housing authority")==1 & recipient_city_name=="CHELSEA"
replace tribe_id=76 if strpos(Tribe, "delaware nation")==1 & recipient_city_name!="ANADARKO"
tab Tribe if tribe_id==76
replace tribe_id=77 if strpos(Tribe, "dresslerville")==1
**note: Dresslerville Colony is missing data!

replace tribe_id=78 if strpos(Tribe, "dry creek")==1
tab Tribe if tribe_id==78
replace tribe_id=79 if strpos(Tribe, "duckwater")==1
tab Tribe if tribe_id==79
replace tribe_id=80 if strpos(Tribe, "eastern cherokee")==1 
replace tribe_id=80 if strpos(Tribe, "eastern band of cherokee indians")==1 
replace tribe_id=80 if strpos(Tribe, "eastern band of cherokee india")==1 
replace tribe_id=80 if Tribe=="eastern band of cherokee i"
tab Tribe if tribe_id==80
replace tribe_id=81 if strpos(Tribe, "eastern shawnee")==1
tab Tribe if tribe_id==81
replace tribe_id=82 if strpos(Tribe, "eastern shoshone")==1
tab Tribe if tribe_id==82

replace tribe_id=83 if strpos(Tribe, "sulphur")==1
replace tribe_id=83 if strpos(Tribe, "elem")==1
tab Tribe if tribe_id==83
replace tribe_id=84 if strpos(Tribe, "elk")==1
tab Tribe if tribe_id==84
replace flag=1 if Tribe=="elk park, town of" | Tribe=="elkhorn city, city of"
replace tribe_id=85 if strpos(Tribe, "elko")==1
tab Tribe if tribe_id==85

replace tribe_id=86 if strpos(Tribe, "ely")==1
tab Tribe if tribe_id==86
replace tribe_id=87 if strpos(Tribe, "enterprise rancheria")==1
tab Tribe if tribe_id==87
replace tribe_id=88 if strpos(Tribe, "ewiiaapaayp")==1
replace tribe_id=88 if strpos(Tribe, "cuyapaipe")==1
tab Tribe if tribe_id==88
replace tribe_id=89 if strpos(Tribe, "graton")==1
replace tribe_id=89 if strpos(Tribe, "federated indians of graton rancheria")==1
replace tribe_id=89 if strpos(Tribe, "fed. indians of graton rancher")==1
tab Tribe if tribe_id==89

replace tribe_id=90 if strpos(Tribe, "flandreau")==1
tab Tribe if tribe_id==90
replace tribe_id=91 if strpos(Tribe, "fond du")==1
tab Tribe if tribe_id==91
replace tribe_id=92 if strpos(Tribe, "forest")==1
replace tribe_id=92 if strpos(Tribe, "forest county potawatomi community")==1
tab Tribe if tribe_id==92
replace tribe_id=93 if strpos(Tribe, "fort belknap")==1
tab Tribe if tribe_id==93
**I believe fort belknap util/solid waste is a tribal enterprise; the recipient city is Fort Belknap Agency.

replace tribe_id=94 if strpos(Tribe, "fort bidwell")==1
replace tribe_id=94 if strpos(Tribe, "ft bidwell indian community co")==1
tab Tribe if tribe_id==94
replace tribe_id=95 if strpos(Tribe, "fort independence")==1
replace tribe_id=95 if strpos(Tribe, "ft independence indian reservation")==1
replace tribe_id=95 if strpos(Tribe, "ft. independence reservation")==1
tab Tribe if tribe_id==95
replace tribe_id=96 if strpos(Tribe, "fort mcdermitt")==1
replace tribe_id=96 if strpos(Tribe, "ft. mcdermitt pauite shoshone tribe")==1
tab Tribe if tribe_id==96
**fort mcdermitt travel plaza enterprise is a tribal enterprise
replace tribe_id=97 if strpos(Tribe, "fort mcdowell")==1
replace tribe_id=97 if strpos(Tribe, "ft mc dowell yavapai nation")==1
tab Tribe if tribe_id==97
**mohave apache is the former name of yavapai

replace tribe_id=98 if strpos(Tribe, "fort mojave")==1
tab Tribe if tribe_id==98
replace tribe_id=99 if strpos(Tribe, "fort sill")==1
replace tribe_id=99 if strpos(Tribe, "ft sill apache tribe of oklahoma")==1
tab Tribe if tribe_id==99
replace tribe_id=100 if strpos(Tribe, "gila river")==1
tab Tribe if tribe_id==100
**gila river farms, gila river broadcasting corporation, gila river telecommunications, inc and gila river healthcare corporation are tribal enterprises
replace tribe_id=101 if strpos(Tribe, "grand portage")==1
tab Tribe if tribe_id==101
replace flag=1 if Tribe=="grand portage"

replace tribe_id=102 if strpos(Tribe, "grand traverse")==1
tab Tribe if tribe_id==102
replace tribe_id=103 if strpos(Tribe, "greenville rancheria")==1
tab Tribe if tribe_id==103
replace tribe_id=104 if strpos(Tribe, "grindstone")==1
tab Tribe if tribe_id==104
replace tribe_id=105 if strpos(Tribe, "guidiville")==1
tab Tribe if tribe_id==105

replace tribe_id=106 if strpos(Tribe, "habematolel")==1
replace tribe_id=106 if strpos(Tribe, "upper lake")==1
tab Tribe if tribe_id==106
replace flag=1 if Tribe=="upper lake rancheria koi"
**Koi nation lives on lower lake rancheria
replace tribe_id=107 if strpos(Tribe, "hannahville")==1
tab Tribe if tribe_id==107
**hannahville health center is affiliated with the tribe
replace tribe_id=108 if strpos(Tribe, "havasupai")==1
tab Tribe if tribe_id==108
replace tribe_id=109 if strpos(Tribe, "ho-chunk")==1
tab Tribe if tribe_id==109
**ho-chunk farms, inc. is a tribal enterprise 
replace tribe_id=110 if strpos(Tribe, "hoh")==1
tab Tribe if tribe_id==110

replace tribe_id=111 if strpos(Tribe, "hoopa valley")==1
tab Tribe if tribe_id==111
**hoopa valley public utilities district is affiliated with the tribe
replace tribe_id=112 if strpos(Tribe, "hopi")==1
replace tribe_id=112 if strpos(Tribe, "the hopi tribe")==1
tab Tribe if tribe_id==112
**hopi credit association, hopi day school, hopi indian credit association, hopi indian tribal council, hopi junior/senior high school, hopi junior/senior high school inc, hopi telecommunications inc, and hopi utilities corporation are tribal enterprises 
replace tribe_id=113 if strpos(Tribe, "hopland")==1
tab Tribe if tribe_id==113
replace tribe_id=114 if strpos(Tribe, "houlton")==1
tab Tribe if tribe_id==114
replace tribe_id=115 if strpos(Tribe, "hualapai")==1
tab Tribe if tribe_id==115
**hualapai detention and rehabilitation... is a tribal program
replace tribe_id=116 if strpos(Tribe, "iipay")==1
replace tribe_id=116 if strpos(Tribe, "santa ysabel")==1
replace tribe_id=116 if strpos(Tribe, "san ysabel")==1
tab Tribe if tribe_id==116
replace tribe_id=117 if strpos(Tribe, "inaja")==1
tab Tribe if tribe_id==117
replace tribe_id=118 if strpos(Tribe, "peaks")==1
replace tribe_id=118 if strpos(Tribe, "indian peaks band of utah paiutes")==1
tab Tribe if tribe_id==118

replace tribe_id=119 if strpos(Tribe, "ione")==1
tab Tribe if tribe_id==119
replace tribe_id=120 if strpos(Tribe, "iowa tribe of kansas and nebraska")==1
replace tribe_id=120 if strpos(Tribe, "united tribes of kansas & southeast nebraska inc")==1
replace tribe_id=120 if strpos(Tribe, "iowa tribe of kansas & nebraska")==1
replace tribe_id=120 if strpos(Tribe, "iowa tribe of kansas and nebra")==1
replace tribe_id=120 if strpos(Tribe, "iowa tribe of ok")==1
tab Tribe if tribe_id==120
replace tribe_id=121 if strpos(Tribe, "iowa tribe of oklahoma")==1
tab Tribe if tribe_id==121

replace tribe_id=122 if strpos(Tribe, "jackson rancheria")==1
tab Tribe if tribe_id==122
replace tribe_id=123 if strpos(Tribe, "jamestown")==1
tab Tribe if tribe_id==123
replace tribe_id=124 if strpos(Tribe, "jamul")==1
tab Tribe if tribe_id==124
replace tribe_id=125 if strpos(Tribe, "jena")==1
tab Tribe if tribe_id==125
replace tribe_id=126 if strpos(Tribe, "jicarilla")==1
tab Tribe if tribe_id==126

replace tribe_id=127 if strpos(Tribe, "kaibab")==1
tab Tribe if tribe_id==127
replace tribe_id=128 if strpos(Tribe, "kalispel")==1
tab Tribe if tribe_id==128
**kalispel business committee is affiliated with the tribe 
replace tribe_id=129 if strpos(Tribe, "kanosh")==1
tab Tribe if tribe_id==129
replace tribe_id=130 if strpos(Tribe, "karuk")==1
tab Tribe if tribe_id==130
**karuk community development corp is affiliated with the tribe
replace tribe_id=131 if strpos(Tribe, "stewarts")==1
replace tribe_id=131 if Tribe=="stwarts point rancheria, kashia bd of pomo in"
replace tribe_id=131 if strpos(Tribe, "kashia")==1
tab Tribe if tribe_id==131
replace tribe_id=132 if strpos(Tribe, "kaw ")==1
replace tribe_id=132 if strpos(Tribe, "the housing authority of the kaw tribe of indians of oklahoma")==1
tab Tribe if tribe_id==132
replace tribe_id=133 if strpos(Tribe, "keechi")==1
**note: Keechi is missing data!
replace tribe_id=134 if strpos(Tribe, "keweenaw")==1
tab Tribe if tribe_id==134
replace flag=1 if Tribe=="keweenaw, county of"
replace tribe_id=135 if strpos(Tribe, "kialegee")==1
tab Tribe if tribe_id==135

replace tribe_id=136 if strpos(Tribe, "kickapoo traditional tribe of texas")==1
replace tribe_id=136 if strpos(Tribe, "kickapoo traditonal tribe of t")==1
replace tribe_id=136 if strpos(Tribe, "texas band of kickapoo")==1
tab Tribe if tribe_id==136
replace tribe_id=137 if strpos(Tribe, "kickapoo tribe in kansas")==1 
replace tribe_id=137 if strpos(Tribe, "kickapoo tribe of kansas")==1 
tab Tribe if tribe_id==137
replace tribe_id=138 if strpos(Tribe, "kickapoo tribe of oklahoma")==1
tab Tribe if tribe_id==138
replace tribe_id=139 if strpos(Tribe, "kiowa")==1
tab Tribe if tribe_id==139
replace flag=1 if Tribe=="kiowa county council on aging, inc." | Tribe=="kiowa young men`s association" | Tribe=="kiowa hud tdhe"
replace tribe_id=140 if strpos(Tribe, "klamath")==1
replace tribe_id=140 if strpos(Tribe, "the klamath tribe")==1
tab Tribe if tribe_id==140
replace flag=1 if Tribe=="klamath river inter tribal fish and water com" | Tribe=="klamath basin area office to install ultrason" | Tribe=="klamath river inter-tribal fish & water commission" | Tribe=="klamath irrigation district" | Tribe=="klamath basin area office to 2008-09 plastic" | Tribe=="klamath 9-1-1 emergency communications district" | Tribe=="klamath river inter tribal fis" | Tribe=="klamath watershed restoration program"
tab Tribe recipient_state_code if tribe_id==140 & flag==0
replace tribe_id=141 if strpos(Tribe, "cortina")==1
replace tribe_id=141 if strpos(Tribe, "kletsel")==1
tab Tribe if tribe_id==141

replace tribe_id=142 if strpos(Tribe, "koi")==1
replace tribe_id=142 if strpos(Tribe, "lower lake rancheria")==1
tab Tribe if tribe_id==142
replace tribe_id=143 if strpos(Tribe, "koosharem")==1
**note: Koosharem Band of Paiutes is missing data!
replace tribe_id=144 if strpos(Tribe, "kootenai")==1
tab Tribe if tribe_id==144
replace flag=1 if Tribe=="kootenai river network"

replace tribe_id=145 if strpos(Tribe, "la jolla")==1
tab Tribe if tribe_id==145
replace tribe_id=146 if strpos(Tribe, "la posta")==1
tab Tribe if tribe_id==146
replace tribe_id=147 if strpos(Tribe, "lac courte")==1
tab Tribe if tribe_id==147
**I'm not 100% sure about "lac courte" and "lac courte oreilles" but I'm keeping them because they are located in the right county (Sawyer county, WI)
replace tribe_id=148 if strpos(Tribe, "lac du flambeau")==1
tab Tribe if tribe_id==148
**"lac du flambeau, town of" is located partially on reservation lands so I'm keeping it
replace tribe_id=149 if strpos(Tribe, "lac vieux")==1
tab Tribe if tribe_id==149
replace tribe_id=150 if strpos(Tribe, "las vegas")==1
tab Tribe if tribe_id==150

replace tribe_id=151 if strpos(Tribe, "leech lake")==1
tab Tribe if tribe_id==151
replace tribe_id=152 if strpos(Tribe, "likely rancheria")==1
**note: Likely Rancheria is missing data but it belongs to the Pit River tribe, for which we do have enrollment data

replace tribe_id=153 if strpos(Tribe, "little river")==1
tab Tribe if tribe_id==153
replace flag=1 if Tribe=="little river  city of"
replace tribe_id=154 if strpos(Tribe, "little shell")==1
tab Tribe if tribe_id==154
replace tribe_id=155 if strpos(Tribe, "little traverse")==1
tab Tribe if tribe_id==155
replace tribe_id=156 if strpos(Tribe, "lone pine")==1
tab Tribe if tribe_id==156
replace tribe_id=157 if strpos(Tribe, "lookout")==1
**note: Lookout Rancheria is missing data but it belongs to the Pit River Tribe, for which we do have enrollment data

replace tribe_id=158 if strpos(Tribe, "los coyotes")==1
tab Tribe if tribe_id==158
**los coyotes looks suspicious but I'll keep it
replace tribe_id=159 if strpos(Tribe, "lovelock")==1
tab Tribe if tribe_id==159
replace tribe_id=160 if strpos(Tribe, "lower brule")==1
tab Tribe if tribe_id==160
**lower brule corporation, lower brule farm corporation, lower brule school district and lower brule wildlife enterprise are tribal enterprises / programs
replace tribe_id=161 if strpos(Tribe, "lower elwha")==1
tab Tribe if tribe_id==161
replace tribe_id=162 if strpos(Tribe, "lower sioux")==1
tab Tribe if tribe_id==162
**lower sioux looks suspicious but I'll keep it
replace tribe_id=163 if strpos(Tribe, "lummi")==1
tab Tribe if tribe_id==163
replace tribe_id=164 if strpos(Tribe, "lytton")==1
tab Tribe if tribe_id==164

replace tribe_id=165 if strpos(Tribe, "makah")==1
tab Tribe if tribe_id==165
**makah museum / makah cultural and research center is owned by the tribe
replace tribe_id=166 if strpos(Tribe, "manchester")==1
tab Tribe if tribe_id==166
replace tribe_id=167 if strpos(Tribe, "manzanita")==1
tab Tribe if tribe_id==167
replace tribe_id=168 if strpos(Tribe, "mashantucket")==1
tab Tribe if tribe_id==168
replace tribe_id=169 if strpos(Tribe, "mashpee")==1
tab Tribe if tribe_id==169
replace tribe_id=170 if strpos(Tribe, "match-e-be-nash-she-wish band")==1
replace tribe_id=170 if strpos(Tribe, "match e be nash she wish band")==1
replace tribe_id=170 if strpos(Tribe, "gun lake")==1
tab Tribe if tribe_id==170

replace tribe_id=171 if strpos(Tribe, "chico")==1
replace tribe_id=171 if strpos(Tribe, "mechoopda")==1
tab Tribe if tribe_id==171
replace flag=1 if Tribe=="chicog fire dept." | Tribe=="chicot county road department"
replace tribe_id=172 if strpos(Tribe, "menominee")==1
replace tribe_id=172 if strpos(Tribe, "college of menominee nation")==1
tab Tribe if tribe_id==172
replace flag=1 if Tribe=="menominee, county of"
replace tribe_id=173 if strpos(Tribe, "mesa")==1
tab Tribe if tribe_id==173
replace tribe_id=174 if strpos(Tribe, "mescalero")==1
tab Tribe if tribe_id==174
**mescalero apache telecom, inc and mescalero school are tribally affiliated
replace tribe_id=175 if strpos(Tribe, "aroostook")==1
tab Tribe if tribe_id==175

replace tribe_id=176 if strpos(Tribe, "miami")==1
tab Tribe if tribe_id==176
replace flag=1 if Tribe=="miami public schools" | Tribe=="miami school district i-23"
replace tribe_id=177 if strpos(Tribe, "miccosukee")==1
tab Tribe if tribe_id==177
**I'm unsire about miccosukee volunteer fire-rescue, inc. and miccosukee corporation but I'll keep them
replace tribe_id=178 if strpos(Tribe, "middletown")==1
tab Tribe if tribe_id==178
replace flag=1 if Tribe=="middletown, city of"
replace tribe_id=179 if strpos(Tribe, "mille lacs")==1
replace tribe_id=179 if strpos(Tribe, "corporate commission of the mille lacs band of ojibwe indians")==1
tab Tribe if tribe_id==179
replace flag=1 if Tribe=="mille lacs health system"
replace tribe_id=180 if strpos(Tribe, "minnesota chippewa")==1
tab Tribe if tribe_id==180

replace tribe_id=181 if strpos(Tribe, "mississippi band of")==1
replace tribe_id=181 if strpos(Tribe, "mississippi band of choctaw indians")==1
replace tribe_id=181 if strpos(Tribe, "choctaw housing authority")==1
replace tribe_id=181 if strpos(Tribe, "miss band of choctaw indians")==1
tab Tribe if tribe_id==181
replace tribe_id=182 if strpos(Tribe, "moapa")==1
tab Tribe if tribe_id==182
replace tribe_id=183 if strpos(Tribe, "modoc")==1
tab Tribe if tribe_id==183
replace tribe_id=184 if strpos(Tribe, "mohegan")==1
replace tribe_id=184 if Tribe=="the mohegan tribe"
tab Tribe if tribe_id==184
replace tribe_id=185 if strpos(Tribe, "monacan")==1
tab Tribe if tribe_id==185

replace tribe_id=186 if strpos(Tribe, "montgomery")==1
tab Tribe if tribe_id==186
replace flag=1 if Tribe=="montgomery county housing authority" | Tribe=="montgomery, county of" | Tribe=="montgomery, town of"
replace tribe_id=187 if strpos(Tribe, "mooretown")==1
tab Tribe if tribe_id==187
replace tribe_id=188 if strpos(Tribe, "morongo")==1
tab Tribe if tribe_id==188
replace tribe_id=189 if strpos(Tribe, "muckleshoot")==1
tab Tribe if tribe_id==189
**muckleshoot federal corporation is tribally owned and located in the same state so I assume it's owned by this particular tribe
replace tribe_id=190 if strpos(Tribe, "nansemond")==1
tab Tribe if tribe_id==190
replace tribe_id=191 if strpos(Tribe, "narragansett")==1
tab Tribe if tribe_id==191
**narragansett looks suspicious but I'll keep it
replace tribe_id=192 if strpos(Tribe, "navajo")==1
replace tribe_id=192 if strpos(Tribe, "the navajo tribe")==1
replace tribe_id=192 if strpos(Tribe, "napi")==1
replace tribe_id=192 if strpos(Tribe, "the navajo nation")==1
replace tribe_id=192 if strpos(Tribe, "the navajo nation tribal gover")==1
replace tribe_id=192 if strpos(Tribe, "the navajo nation tribal government")==1
tab Tribe if tribe_id==192
**navajo transitional energy company, llc belongs to the tribe; 
**I'm unsure about navajo mountain water users association but I'll keep it;
**navajo mountain community  is fully on the reservation so I'll keep it;
**navajo health foundation-sage memorial hospital is independent but fully managed by tribal members, I'll flag it
replace flag=1 if Tribe=="navajo health foundation-sage memorial hospital inc"
**navajo agricultural projects industry (napi) is owned by navajo nation;
**navajo area agency on aging belongs to the tribe
**navajo engineering & construction authority belongs to the tribe;
replace tribe_id=193 if strpos(Tribe, "nez perce")==1
replace tribe_id=193 if strpos(Tribe, "nez perc tribe")==1
replace tribe_id=193 if strpos(Tribe, "nez pierce tribe")==1
tab Tribe if tribe_id==193
**nez perce tourism, llc appears to be a private enterprise 
replace flag=1 if Tribe=="nez perce tourism, llc"
replace tribe_id=194 if strpos(Tribe, "nisqually")==1
replace tribe_id=194 if Tribe=="nisquarlly indian tribe"
tab Tribe if tribe_id==194
replace tribe_id=195 if strpos(Tribe, "nooksack")==1
tab Tribe if tribe_id==195

replace tribe_id=196 if strpos(Tribe, "northern arapaho")==1
replace tribe_id=196 if strpos(Tribe, "sky people northern arapaho tribe")==1
tab Tribe if tribe_id==196
replace tribe_id=197 if strpos(Tribe, "northern cheyenne")==1
tab Tribe if tribe_id==197
**northern cheyenne busby school is a tribally owned school 
**northern cheyenne utilities commission appears tribally owned
replace tribe_id=198 if strpos(Tribe, "northfork")==1
replace tribe_id=198 if strpos(Tribe, "north fork")==1 
tab Tribe if tribe_id==198
replace flag=1 if Tribe=="northfork community fire department, inc"
replace tribe_id=199 if strpos(Tribe, "nw band of shoshoni nation")==1
replace tribe_id=199 if strpos(Tribe, "nw band of shoshone nation")==1
replace tribe_id=199 if strpos(Tribe, "northwestern band of the shoshon nation")==1
replace tribe_id=199 if strpos(Tribe, "northwestern band of shoshoni nation")==1
replace tribe_id=199 if Tribe=="nw shoshone economic development corporation"
replace tribe_id=199 if Tribe=="northwestern band of shoshone nation"
tab Tribe if tribe_id==199
replace tribe_id=200 if strpos(Tribe, "huron")==1
replace tribe_id=200 if strpos(Tribe, "nottawaseppi")==1
tab Tribe if tribe_id==200
**huron potawatomi inc is the tribe
replace flag=1 if Tribe=="huron, city of"
replace tribe_id=201 if strpos(Tribe, "oglala")==1
replace tribe_id=201 if strpos(Tribe, "sd oglala sioux")==1
replace tribe_id=201 if Tribe=="ogala sioux tribe"
tab Tribe if tribe_id==201
**oglala oyate woitancan empowerment zone was the reservation status
**oglala sioux parks & recreation is tribally owned
replace tribe_id=202 if strpos(Tribe, "ohkay")==1
replace tribe_id=202 if Tribe=="okay owingeh"
replace tribe_id=202 if strpos(Tribe, "san juan pueblo")==1
replace tribe_id=202 if strpos(Tribe, "pueblo of san juan")==1
tab Tribe if tribe_id==202
replace tribe_id=203 if strpos(Tribe, "omaha")==1
tab Tribe if tribe_id==203
replace flag=1 if Tribe=="omaha-council bluffs metropolitan area planning agency"

replace tribe_id=204 if strpos(Tribe, "oneida nation")==1 & recipient_state_code=="NY"
replace tribe_id=204 if strpos(Tribe, "oneida indian nation")==1
replace tribe_id=205 if Tribe=="onsin oneida tribe of wisc"
tab Tribe if tribe_id==204
tab Tribe recipient_state_code if tribe_id==204

replace tribe_id=205 if strpos(Tribe, "oneida tribe of wisconsin")==1
replace tribe_id=205 if strpos(Tribe, "oneida tribe of indians of wis")==1
replace tribe_id=205 if strpos(Tribe, "oneida tribe of indians of wisconsin")==1
replace tribe_id=205 if strpos(Tribe, "oneida tribe of wi")==1
replace tribe_id=205 if strpos(Tribe, "oneida nation")==1 & recipient_state_code=="WI"
replace tribe_id=205 if strpos(Tribe, "oneida nation farms")==1
replace tribe_id=205 if strpos(Tribe, "oneida")==1
replace tribe_id=205 if strpos(Tribe, "oneida tribal school")==1
replace tribe_id=205 if strpos(Tribe, "oneida housing authority")==1
replace flag=1 if Tribe=="oneida indian society, inc."
replace flag=1 if Tribe=="oneida county hospital foundation, inc."
tab Tribe if tribe_id==205
tab Tribe recipient_state_code if tribe_id==205

replace tribe_id=206 if strpos(Tribe, "onondaga")==1
tab Tribe if tribe_id==206
replace flag=1 if Tribe=="onondaga county resource recovery agency inc"
replace tribe_id=207 if strpos(Tribe, "otoe-")==1
replace tribe_id=207 if strpos(Tribe, "otoe missouria tribe of oklaho")==1
tab Tribe if tribe_id==207
replace tribe_id=208 if strpos(Tribe, "ottawa tribe")==1
replace tribe_id=208 if strpos(Tribe, "ottawa indian tribe of oklahoma")==1 
tab Tribe if tribe_id==208

replace tribe_id=209 if strpos(Tribe, "paiute indian tribe of utah")==1
tab Tribe if tribe_id==209
replace tribe_id=210 if strpos(Tribe, "fallon")==1
replace tribe_id=210 if strpos(Tribe, "shoshone-paiute")==1
tab Tribe if tribe_id==210
**note: shoshone-paiute tribes should be assigned tribe_id=299 (from primary place of performance variable)
replace tribe_id=211 if strpos(Tribe, "pala band")==1
tab Tribe if tribe_id==211
replace tribe_id=212 if strpos(Tribe, "pamunkey")==1
tab Tribe if tribe_id==212
replace tribe_id=213 if strpos(Tribe, "pascua")==1
replace tribe_id=213 if Tribe=="pasqua yaqui tribe"
tab Tribe if tribe_id==213
replace tribe_id=214 if strpos(Tribe, "paskenta")==1
tab Tribe if tribe_id==214
replace tribe_id=215 if strpos(Tribe, "passamaquoddy tribe")==1
replace tribe_id=215 if strpos(Tribe, "passamaquoddy tribe indian")==1
replace tribe_id=215 if strpos(Tribe, "indian township tribal government")==1
replace tribe_id=215 if strpos(Tribe, "pleasant point")==1
replace tribe_id=215 if strpos(Tribe, "passamaquoddy joint tribal council")==1
replace tribe_id=215 if strpos(Tribe, "indian township passamaquoddy ha")==1
**Passamaquoddy Tribe, Passamaquoddy Tribe - Indian Township, and Passamaquoddy Tribe - Pleasant Point were combined
tab Tribe if tribe_id==215

replace tribe_id=218 if strpos(Tribe, "pauma")==1
tab Tribe if tribe_id==218
replace tribe_id=219 if strpos(Tribe, "pawnee")==1
tab Tribe if tribe_id==219
replace tribe_id=220 if strpos(Tribe, "pechanga")==1
tab Tribe if tribe_id==220
replace tribe_id=221 if strpos(Tribe, "penobscot")==1
tab Tribe if tribe_id==221
replace tribe_id=222 if strpos(Tribe, "peoria")==1
tab Tribe if tribe_id==222

replace tribe_id=223 if strpos(Tribe, "picayune")==1
replace tribe_id=223 if Tribe=="chukchansi indian housing authority"
tab Tribe if tribe_id==223
replace tribe_id=224 if strpos(Tribe, "pinoleville")==1
tab Tribe if tribe_id==224
replace tribe_id=225 if strpos(Tribe, "pit river")==1
tab Tribe if tribe_id==225
replace flag=1 if Tribe=="pit river health service  inc" | Tribe=="pit river health service inc" | Tribe=="pit river health service, inc"
replace tribe_id=226 if strpos(Tribe, "poarch band")==1
replace tribe_id=226 if strpos(Tribe, "poarch creek indians")==1
tab Tribe if tribe_id==226
replace tribe_id=227 if strpos(Tribe, "pokagon")==1
replace tribe_id=227 if strpos(Tribe, "kokagon band of potawatomi")==1
tab Tribe if tribe_id==227

replace tribe_id=228 if strpos(Tribe, "ponca tribe of oklahoma")==1
replace tribe_id=228 if strpos(Tribe, "ponca tribe of indians of oklahoma")==1
tab Tribe if tribe_id==228
replace tribe_id=229 if strpos(Tribe, "ponca tribe of nebraska")==1
replace tribe_id=229 if strpos(Tribe, "ponca economic development cor")==1
tab Tribe if tribe_id==229
replace tribe_id=230 if strpos(Tribe, "port gamble")==1
replace tribe_id=230 if strpos(Tribe, "pt gamble sklallam housing aut")==1
tab Tribe if tribe_id==230
replace tribe_id=231 if strpos(Tribe, "potter valley")==1
tab Tribe if tribe_id==231
replace tribe_id=232 if strpos(Tribe, "prairie band")==1
tab Tribe if tribe_id==232
replace tribe_id=233 if strpos(Tribe, "prairie island")==1
replace tribe_id=233 if strpos(Tribe, "the prairie island indian community")==1
tab Tribe if tribe_id==233

replace tribe_id=234 if strpos(Tribe, "acoma")==1
replace tribe_id=234 if strpos(Tribe, "pueblo of acoma")==1
replace tribe_id=234 if strpos(Tribe, "pueblo of acoma (inc)")==1
replace tribe_id=234 if strpos(Tribe, "pueblo of acoma housing authority")==1
replace tribe_id=234 if strpos(Tribe, "pueblo of acoma police department")==1
replace tribe_id=234 if strpos(Tribe, "pueblo de acoma tribal council")==1
tab Tribe if tribe_id==234
**pueblo of acoma police department appears to be owned by the tribe
replace flag=1 if Tribe=="acoma canoncito laguna hospital"
replace flag=1 if Tribe=="acoma cattle growers association" | Tribe=="acoma land and cattle company" | Tribe=="acoma livestock growers organization"
replace flag=1 if Tribe=="acoma number 8 ranch"
**acoma cattle growers association appears separate from the tribe

replace tribe_id=235 if strpos(Tribe, "cochiti")==1
replace tribe_id=235 if strpos(Tribe, "pueblo de cochiti")==1
tab Tribe if tribe_id==235
replace tribe_id=236 if strpos(Tribe, "isleta")==1
replace tribe_id=236 if strpos(Tribe, "pueblo of isleta")==1
tab Tribe if tribe_id==236
replace tribe_id=237 if strpos(Tribe, "jemez")==1
replace tribe_id=237 if strpos(Tribe, "pueblo of jemez")==1
replace tribe_id=237 if strpos(Tribe, "pueblo of jemz")==1
tab Tribe if tribe_id==237

replace tribe_id=238 if strpos(Tribe, "laguna")==1
replace tribe_id=238 if strpos(Tribe, "pueblo of laguna")==1
tab Tribe if tribe_id==238
replace flag=1 if Tribe=="laguna de santa rosa foundation" 
**laguna rainbow corp appears to be a tribe entity
**laguna economic advancement is tribally owned
replace tribe_id=239 if strpos(Tribe, "nambe")==1
replace tribe_id=239 if strpos(Tribe, "pueblo of nambe")==1
tab Tribe if tribe_id==239
replace flag=1 if Tribe=="nambe pueblo hi-tech"
replace tribe_id=240 if strpos(Tribe, "picuris")==1
replace tribe_id=240 if strpos(Tribe, "pueblo of picuris")==1
tab Tribe if tribe_id==240
replace tribe_id=241 if strpos(Tribe, "pojoaque")==1
replace tribe_id=241 if strpos(Tribe, "pajoaque")==1
replace tribe_id=241 if strpos(Tribe, "pueblo of pojoaque")==1
replace tribe_id=241 if strpos(Tribe, "pueblo of pojoaque")==1
tab Tribe if tribe_id==241

replace tribe_id=242 if strpos(Tribe, "san felipe")==1
replace tribe_id=242 if strpos(Tribe, "pueblo of san felipe")==1
tab Tribe if tribe_id==242
replace tribe_id=243 if strpos(Tribe, "san ildefonso")==1
replace tribe_id=243 if strpos(Tribe, "pueblo de san ildefonso")==1
tab Tribe if tribe_id==243
**san ildefonso services llc is tribally owned
replace tribe_id=244 if strpos(Tribe, "sandia")==1
replace tribe_id=244 if strpos(Tribe, "pueblo of sandia")==1
tab Tribe if tribe_id==244

replace tribe_id=245 if strpos(Tribe, "santa ana")==1
replace tribe_id=245 if strpos(Tribe, "pueblo of santa ana")==1
tab Tribe if tribe_id==245
replace flag=1 if Tribe=="santa ana, city of"
replace tribe_id=246 if strpos(Tribe, "santa clara")==1
replace tribe_id=246 if strpos(Tribe, "pueblo of santa clara")==1
tab Tribe if tribe_id==246
replace flag=1 if Tribe=="santa clara cnty housing auth" 
**santa clara day school is owned by the tribe
**I'm unsure about "santa clara" but I'll keep it
replace tribe_id=247 if strpos(Tribe, "taos")==1
replace tribe_id=247 if strpos(Tribe, "pueblo of taos")==1
tab Tribe if tribe_id==247
replace flag=1 if Tribe=="taos county economic development corp"

replace tribe_id=248 if strpos(Tribe, "tesuque")==1
replace tribe_id=248 if strpos(Tribe, "pueblo of tesuque")==1
tab Tribe if tribe_id==248
replace tribe_id=249 if strpos(Tribe, "zia")==1
replace tribe_id=249 if strpos(Tribe, "pueblo of zia")==1
tab Tribe if tribe_id==249
replace flag=1 if Tribe=="zia therapy center inc"
replace tribe_id=250 if strpos(Tribe, "puyallup")==1
tab Tribe if tribe_id==250
replace flag=1 if Tribe=="puyallup school district"
replace tribe_id=251 if strpos(Tribe, "pyramid")==1
tab Tribe if tribe_id==251
**pyramid lake jr/sr high school is a tribal school
**I'm unsure about "pyramid lake" but I'll keep it
replace tribe_id=252 if strpos(Tribe, "quapaw")==1
tab Tribe if tribe_id==252
replace flag=1 if Tribe=="quapaw public schools"
replace tribe_id=253 if strpos(Tribe, "quartz")==1
replace tribe_id=253 if strpos(Tribe, "quarta valley indian reservation")==1
tab Tribe if tribe_id==253
replace tribe_id=254 if strpos(Tribe, "quechan")==1
replace tribe_id=254 if strpos(Tribe, "the quechan tribe")==1
tab Tribe if tribe_id==254
replace tribe_id=255 if strpos(Tribe, "quileute")==1
replace tribe_id=255 if strpos(Tribe, "quiluete tribal school board")==1
tab Tribe if tribe_id==255
replace tribe_id=256 if strpos(Tribe, "quinault")==1
replace tribe_id=256 if strpos(Tribe, "quinalt indian nation")==1
tab Tribe if tribe_id==256

replace tribe_id=257 if strpos(Tribe, "ramona")==1
tab Tribe if tribe_id==257
replace tribe_id=258 if strpos(Tribe, "rappahannock")==1
tab Tribe if tribe_id==258
replace tribe_id=259 if strpos(Tribe, "red cliff")==1
tab Tribe if tribe_id==259
replace tribe_id=260 if strpos(Tribe, "red lake")==1
tab Tribe if tribe_id==260
**red lake builders inc appears to be a tribal enterprise
**red lake comprehensive health services appears to be owned by the tribe
**red lake homeless shelter inc appears to be tribally owned
replace tribe_id=261 if strpos(Tribe, "redding")==1
tab Tribe if tribe_id==261
replace tribe_id=262 if strpos(Tribe, "redwood")==1
tab Tribe if tribe_id==262
replace tribe_id=263 if strpos(Tribe, "reno-sparks")==1
replace tribe_id=263 if strpos(Tribe, "reno sparks indian colony")==1
replace tribe_id=263 if strpos(Tribe, "reno sparks tribal council")==1
tab Tribe if tribe_id==263

replace tribe_id=264 if strpos(Tribe, "resighini")==1
tab Tribe if tribe_id==264
replace tribe_id=265 if strpos(Tribe, "rincon")==1
tab Tribe if tribe_id==265
replace tribe_id=266 if strpos(Tribe, "roaring")==1
**note: Roaring Creek Rancheria is missing data but it belongs to the Pit River tribe for which we do have enrollment data
replace tribe_id=267 if strpos(Tribe, "robinson")==1
tab Tribe if tribe_id==267
replace tribe_id=268 if strpos(Tribe, "rosebud")==1
tab Tribe if tribe_id==268
replace tribe_id=269 if strpos(Tribe, "round valley")==1
replace tribe_id=269 if strpos(Tribe, "covelo indian community council")==1
tab Tribe if tribe_id==269
**round valley indian health center, inc. appears independent
replace flag=1 if Tribe=="round valley indian health center, inc."
replace flag=1 if Tribe=="round valley unified school district"
replace tribe_id=270 if strpos(Tribe, "sac & fox nation of missouri in kansas")==1
replace tribe_id=270 if strpos(Tribe, "sac and fox tribe of missouri")==1
replace tribe_id=270 if Tribe=="housing authority of sac & fox"
replace tribe_id=270 if Tribe=="hsg auth of sac & fox"
tab Tribe if tribe_id==270
replace tribe_id=271 if strpos(Tribe, "sac & fox nation")==1
replace tribe_id=271 if strpos(Tribe, "sac and fox nation")==1
replace tribe_id=270 if Tribe=="sac & fox nation of missou"
replace tribe_id=270 if Tribe=="sac & fox nation of missouri in kansas"
tab Tribe if tribe_id==271
replace tribe_id=272 if strpos(Tribe, "sac & fox tribe of the mississippi in iowa")==1
replace tribe_id=272 if Tribe=="sac and fox tribe of the"
tab Tribe if tribe_id==272

replace tribe_id=273 if strpos(Tribe, "saginaw")==1
tab Tribe if tribe_id==273
replace tribe_id=274 if strpos(Tribe, "regis")==1
replace tribe_id=274 if strpos(Tribe, "saint regis mohawk tribe")==1
replace tribe_id=274 if strpos(Tribe, "st regis mohawk tribal community")==1
replace tribe_id=274 if strpos(Tribe, "st regis mohawk tribe")==1
replace tribe_id=274 if strpos(Tribe, "st. regis mohawk education and community fund, inc.")==1
replace tribe_id=274 if strpos(Tribe, "st. regis mohawk tribe")==1
tab Tribe if tribe_id==274
replace tribe_id=275 if strpos(Tribe, "salt river")==1
replace tribe_id=275 if strpos(Tribe, "saddleback communications")==1
tab Tribe if tribe_id==275
replace flag=1 if Tribe=="salt river financial services institution"
replace tribe_id=276 if strpos(Tribe, "samish")==1
tab Tribe if tribe_id==276
replace tribe_id=277 if strpos(Tribe, "san carlos")==1
replace tribe_id=277 if strpos(Tribe, "the san carlos apache tribe")==1
tab Tribe if tribe_id==277
**san carlos apache healthcare corporation appears to be tribally owned 
replace tribe_id=278 if strpos(Tribe, "san juan southern paiute tribe")==1
tab Tribe if tribe_id==278
replace tribe_id=279 if strpos(Tribe, "san pasqual")==1
tab Tribe if tribe_id==279
replace tribe_id=280 if strpos(Tribe, "santa rosa band")==1
tab Tribe if tribe_id==280

replace tribe_id=281 if strpos(Tribe, "santa rosa rancheria")==1
tab Tribe if tribe_id==281
replace tribe_id=282 if strpos(Tribe, "santa ynez")==1
tab Tribe if tribe_id==282
replace tribe_id=283 if strpos(Tribe, "santee")==1
tab Tribe if tribe_id==283
**santee  village of is the principal village of the reservation
replace tribe_id=284 if strpos(Tribe, "santo domingo")==1 
replace tribe_id=284 if strpos(Tribe, "pueblo of santo domingo")==1 
replace tribe_id=284 if Tribe=="santo dominto tribe" 
replace tribe_id=284 if strpos(Tribe, "kewa pueblo")==1 
tab Tribe if tribe_id==284
replace tribe_id=285 if strpos(Tribe, "sauk")==1
tab Tribe if tribe_id==285
replace tribe_id=286 if strpos(Tribe, "sault")==1
tab Tribe if tribe_id==286
replace flag=1 if Tribe=="sault sainte marie, city of" 
replace tribe_id=287 if strpos(Tribe, "scotts")==1
tab Tribe if tribe_id==287
replace tribe_id=288 if strpos(Tribe, "seminole tribe")==1
tab Tribe if tribe_id==288

replace tribe_id=289 if strpos(Tribe, "seneca nation")==1
tab Tribe if tribe_id==289
replace tribe_id=290 if strpos(Tribe, "seneca cayuga")==1
replace tribe_id=290 if strpos(Tribe, "seneca-cayuga tribe of oklahoma")==1
replace tribe_id=290 if strpos(Tribe, "senecacayuga tribe of oklahoma")==1
tab Tribe if tribe_id==290
replace tribe_id=291 if strpos(Tribe, "shakopee")==1
tab Tribe if tribe_id==291

replace tribe_id=292 if strpos(Tribe, "shawnee tribe")==1
tab Tribe if tribe_id==292
replace tribe_id=293 if strpos(Tribe, "sherwood")==1
tab Tribe if tribe_id==293
replace tribe_id=294 if strpos(Tribe, "shingle springs")==1
tab Tribe if tribe_id==294
replace tribe_id=295 if strpos(Tribe, "shinnecock")==1
tab Tribe if tribe_id==295
replace tribe_id=296 if strpos(Tribe, "shivwits")==1
tab Tribe if tribe_id==296

replace tribe_id=297 if strpos(Tribe, "shoalwater")==1
replace tribe_id=297 if strpos(Tribe, "shoal water bay tribe")==1
tab Tribe if tribe_id==297
replace tribe_id=298 if strpos(Tribe, "shoshone-bannock")==1
replace tribe_id=298 if strpos(Tribe, "shoshone bannock")==1
replace tribe_id=298 if strpos(Tribe, "fort hall")==1
tab Tribe if tribe_id==298

replace tribe_id=299 if strpos(Tribe, "duck valley")==1
replace tribe_id=299 if strpos(Tribe, "shoshone paiute tribes of duck valley")==1
replace tribe_id=299 if strpos(Tribe, "shoshone-paiute tribes")==1 
replace tribe_id=299 if strpos(Tribe, "shoshone paiute tribes")==1 
tab Tribe if tribe_id==299
replace tribe_id=300 if strpos(Tribe, "sisseton")==1
tab Tribe if tribe_id==300
replace tribe_id=301 if strpos(Tribe, "skokomish")==1
tab Tribe if tribe_id==301

replace tribe_id=302 if strpos(Tribe, "skull valley")==1
tab Tribe if tribe_id==302
**skull valley health clinic, inc. is owned by the tribe
replace tribe_id=303 if strpos(Tribe, "snoq")==1
tab Tribe if tribe_id==303
replace tribe_id=304 if strpos(Tribe, "soboba")==1
tab Tribe if tribe_id==304
replace tribe_id=305 if strpos(Tribe, "sokaogon")==1
replace tribe_id=305 if strpos(Tribe, "sokaogon chippewa")==1
replace tribe_id=305 if strpos(Tribe, "sokaogan chippewa community")==1
tab Tribe if tribe_id==305
replace tribe_id=306 if strpos(Tribe, "south fork band")==1
tab Tribe if tribe_id==306
**south fork band environmental appears to be owned by the tribe

replace tribe_id=307 if strpos(Tribe, "southern ute")==1
tab Tribe if tribe_id==307
replace tribe_id=308 if strpos(Tribe, "spirit lake")==1
replace tribe_id=308 if strpos(Tribe, "devils lake sioux")==1
tab Tribe if tribe_id==308
replace tribe_id=309 if strpos(Tribe, "spokane")==1
tab Tribe if tribe_id==309
replace tribe_id=310 if strpos(Tribe, "squaxin")==1
tab Tribe if tribe_id==310
replace tribe_id=311 if strpos(Tribe, "saint croix")==1
replace tribe_id=311 if strpos(Tribe, "st croix chippewa indians of wisconsin")==1
replace tribe_id=311 if strpos(Tribe, "st croix indian tribe")==1
replace tribe_id=311 if strpos(Tribe, "st. croix chippewa ha")==1
replace tribe_id=311 if strpos(Tribe, "st. croix chippewa indians of wisconsin")==1
replace tribe_id=311 if strpos(Tribe, "st. croix tribal council")==1
replace tribe_id=311 if strpos(Tribe, "st croix chippewa housing")==1
replace tribe_id=311 if strpos(Tribe, "st croix tribal council et")==1
tab Tribe if tribe_id==311
replace tribe_id=312 if strpos(Tribe, "standing rock")==1
replace tribe_id=312 if strpos(Tribe, "standings rock sioux tribe com")==1
tab Tribe if tribe_id==312
**standing rock farms is owned by the tribe
**standing rock telecommunications, inc is owned by the tribe
**standing rock renewable energy power authority is owned by the tribe
replace tribe_id=313 if strpos(Tribe, "stewarts point")==1
tab Tribe if tribe_id==313

replace tribe_id=314 if strpos(Tribe, "stilla")==1
tab Tribe if tribe_id==314
**stillaguamish board of directors appears to be the tribe
replace tribe_id=315 if strpos(Tribe, "stockbridge")==1
tab Tribe if tribe_id==315
replace tribe_id=316 if strpos(Tribe, "summit lake paiute")==1
tab Tribe if tribe_id==316
replace tribe_id=317 if strpos(Tribe, "suquamish")==1
replace tribe_id=317 if strpos(Tribe, "the suquamish tribe")==1
tab Tribe if tribe_id==317
replace tribe_id=318 if strpos(Tribe, "susanville")==1
tab Tribe if tribe_id==318
replace tribe_id=319 if strpos(Tribe, "swino")==1
tab Tribe if tribe_id==319

replace tribe_id=320 if strpos(Tribe, "sycuan")==1
tab Tribe if tribe_id==320
**Sycuan Inter-Tribal Vocational Rehabilitation appears to be affiliated with the tribe
**sycuan medical dental center is a tribal department
replace tribe_id=321 if strpos(Tribe, "table mountain")==1
tab Tribe if tribe_id==321
replace tribe_id=322 if strpos(Tribe, "tawak")==1
**note: Tawakonie is missing data!

replace tribe_id=323 if strpos(Tribe, "te-moak")==1
replace tribe_id=323 if strpos(Tribe, "te moak tribe-western shoshone")==1
replace tribe_id=323 if strpos(Tribe, "battle mountain band council")==1
tab Tribe if tribe_id==323
replace tribe_id=324 if strpos(Tribe, "tejon")==1
tab Tribe if tribe_id==324
replace tribe_id=325 if strpos(Tribe, "chickasaw")==1
replace tribe_id=325 if strpos(Tribe, "the chickasaw nation")==1
replace tribe_id=325 if strpos(Tribe, "chikasaw nation")==1
tab Tribe if tribe_id==325
replace flag=1 if Tribe=="chickasaw foundation"
replace tribe_id=326 if strpos(Tribe, "choctaw nation of oklahoma")==1
replace tribe_id=326 if Tribe=="housing authority of choctaw nations"
replace tribe_id=326 if Tribe=="housing authority of  choctaw nation of oklahoma"
tab Tribe if tribe_id==326
replace tribe_id=327 if strpos(Tribe, "muscogee")==1
replace tribe_id=327 if strpos(Tribe, "creek nation")==1
replace tribe_id=327 if strpos(Tribe, "creek tribe of oklahoma")==1
tab Tribe if tribe_id==327
replace flag=1 if Tribe=="muscogee nation of florida, inc." 
**they are a state-recognized tribe
replace tribe_id=328 if strpos(Tribe, "osage")==1
tab Tribe if tribe_id==328
replace tribe_id=329 if strpos(Tribe, "seminole nation")==1
replace tribe_id=329 if strpos(Tribe, "housing authority of seminole nation")==1
tab Tribe if tribe_id==329
replace tribe_id=330 if strpos(Tribe, "thlop")==1
tab Tribe if tribe_id==330
replace tribe_id=331 if strpos(Tribe, "fort berthold")==1
replace tribe_id=331 if strpos(Tribe, "three affiliated tribes")==1
tab Tribe if tribe_id==331
replace tribe_id=332 if strpos(Tribe, "timbisha shoshone")==1
tab Tribe if tribe_id==332

replace tribe_id=333 if strpos(Tribe, "tohono")==1
replace tribe_id=333 if strpos(Tribe, "the tohono o'odham nation")==1
replace tribe_id=333 if strpos(Tribe, "cdfi of the tohono o'odham nation")==1
replace tribe_id=333 if Tribe=="tohona o'odham nation"
tab Tribe if tribe_id==333
**tohono o odham ki-ki association is tribe-affiliated
**tohono o' odham community action appears to be a stand-alone org
replace flag=1 if Tribe=="tohono o' odham community action"
**tohono o'odham farming authority is tribally owned
replace tribe_id=334 if strpos(Tribe, "smith river")==1
replace tribe_id=334 if strpos(Tribe, "tolowa")==1
tab Tribe if tribe_id==334
replace tribe_id=335 if strpos(Tribe, "tonawanda")==1
**Note: Tonawanda is missing data!
replace tribe_id=336 if strpos(Tribe, "tonkaw")==1
tab Tribe if tribe_id==336
replace flag=1 if Tribe=="tonkawa development authority inc"
replace tribe_id=337 if strpos(Tribe, "tonto")==1
tab Tribe if tribe_id==337

replace tribe_id=338 if strpos(Tribe, "torres")==1
tab Tribe if tribe_id==338
replace tribe_id=339 if strpos(Tribe, "tulalip")==1
replace tribe_id=339 if strpos(Tribe, "the tulalip tribes of washington")==1
replace tribe_id=339 if strpos(Tribe, "the tulalip tribe")==1
tab Tribe if tribe_id==339
replace flag=1 if Tribe=="tulalip foundation"
replace tribe_id=340 if strpos(Tribe, "tule river")==1
tab Tribe if tribe_id==340
**tule river economic development corpo. is tribally owned
replace flag=1 if Tribe=="tule river indian health center, inc."
replace tribe_id=341 if strpos(Tribe, "tunica")==1
tab Tribe if tribe_id==341
replace tribe_id=342 if strpos(Tribe, "tuolum")==1
replace tribe_id=342 if strpos(Tribe, "the tuolumne band of me-wuk indians")==1
tab Tribe if tribe_id==342
**tuolumne me-wuk indian health center is affiliated with the tribe
replace tribe_id=343 if strpos(Tribe, "turtle")==1
tab Tribe if tribe_id==343
**Im unsure about turtle mountain tribal arts association and I'll drop it
replace flag=1 if Tribe=="turtle mountain tribal arts association"
**I'm unsure about turtle mountain public utilities comm but I'll keep it
replace tribe_id=344 if strpos(Tribe, "tuscar")==1
tab Tribe if tribe_id==344
replace flag=1 if Tribe=="tuscarawas metropolitan housing"
replace tribe_id=345 if strpos(Tribe, "twenty")==1
tab Tribe if tribe_id==345
replace tribe_id=346 if strpos(Tribe, "auburn")==1
replace tribe_id=346 if strpos(Tribe, "united auburn indian community")==1
tab Tribe if tribe_id==346
replace flag=1 if Tribe=="auburn memorial library foundation inc"
replace tribe_id=347 if strpos(Tribe, "keetoowah")==1
replace tribe_id=347 if strpos(Tribe, "united keetoowah band")==1
replace tribe_id=347 if strpos(Tribe, "united keetoowah band of cherokee")==1
tab Tribe if tribe_id==347
**I'm unsure about keetoowah economic development author. but I'll keep it
replace tribe_id=348 if strpos(Tribe, "mattaponi")==1
replace tribe_id=348 if strpos(Tribe, "upper mattaponi indian tribe")==1
tab Tribe if tribe_id==348
replace flag=1 if Tribe=="mattaponi-pamunkey-monacan consortium"

replace tribe_id=349 if strpos(Tribe, "upper sioux")==1
tab Tribe if tribe_id==349
replace tribe_id=350 if strpos(Tribe, "upper skagit")==1
replace tribe_id=350 if Tribe=="uper skagit tribe"
tab Tribe if tribe_id==350
replace tribe_id=351 if strpos(Tribe, "uintah")==1
replace tribe_id=351 if strpos(Tribe, "ute indian tribe")==1
tab Tribe if tribe_id==351
replace flag=1 if Tribe=="uintah indian irrigation project operation and maintenance company"
replace tribe_id=352 if strpos(Tribe, "ute mountain")==1
tab Tribe if tribe_id==352
replace tribe_id=353 if strpos(Tribe, "utu utu")==1
replace tribe_id=353 if strpos(Tribe, "benton paiute reservation")==1
tab Tribe if tribe_id==353
replace tribe_id=354 if strpos(Tribe, "viejas")==1
tab Tribe if tribe_id==354
replace tribe_id=355 if strpos(Tribe, "waco")==1
**note: Waco is missing data!

replace tribe_id=356 if strpos(Tribe, "walker river")==1
tab Tribe if tribe_id==356
replace tribe_id=357 if strpos(Tribe, "wampa")==1
replace tribe_id=357 if strpos(Tribe, "aquinnah wampanoag judiciary")==1
replace tribe_id=357 if strpos(Tribe, "aquinnah wampanoag tribal housing authority")==1
tab Tribe if tribe_id==357
replace tribe_id=358 if strpos(Tribe, "washoe ranches")==1
**note: Washoe Ranches is missing data!
replace tribe_id=359 if strpos(Tribe, "washoe")==1
tab Tribe if tribe_id==359
**washoe housing authority is owned by washoe tribe and also serves Carson Colony, Stewart Community, Dresslerville Community, and Woodfords Community. 
replace flag=1 if Tribe=="washoe county"
replace tribe_id=360 if strpos(Tribe, "wells")==1
tab Tribe if tribe_id==360
replace flag=1 if Tribe=="wells family resource center"
replace flag=1 if Tribe=="wellsville-mendon conservation district"
replace tribe_id=361 if strpos(Tribe, "white earth")==1
tab Tribe if tribe_id==361
replace flag=1 if Tribe=="white earth land recovery project"
replace tribe_id=362 if strpos(Tribe, "white mountain apache")==1
replace tribe_id=362 if strpos(Tribe, "white mountaim apache tribe")==1
tab Tribe if tribe_id==362
**apache behavioral health services inc appears indepepndent from the tribe
replace flag=1 if Tribe=="apache behavioral health services inc"
replace tribe_id=363 if strpos(Tribe, "wichita tribe")==1
**note: Wichita is missing data!
replace tribe_id=364 if strpos(Tribe, "wichita &")==1
replace tribe_id=364 if strpos(Tribe, "wichita and")==1
tab Tribe if tribe_id==364
replace tribe_id=365 if strpos(Tribe, "wilton")==1
tab Tribe if tribe_id==365

replace tribe_id=366 if strpos(Tribe, "winnebago")==1
tab Tribe if tribe_id==366
**winnebago housing & development commission was created by the tribe
replace flag=1 if Tribe=="winnebago county forest perserve" | Tribe=="winnebago county housing authority"
replace tribe_id=367 if strpos(Tribe, "winnemucca")==1
tab Tribe if tribe_id==367
replace tribe_id=368 if strpos(Tribe, "table bluff")==1
replace tribe_id=368 if strpos(Tribe, "wiyot")==1
tab Tribe if tribe_id==368
replace tribe_id=369 if strpos(Tribe, "woodfords")==1
**note: Woodfords Community is missing data!
replace tribe_id=370 if strpos(Tribe, "wyandotte")==1
tab Tribe if tribe_id==370
replace tribe_id=371 if strpos(Tribe, "xl ranch")==1
**note: XL Ranch Rancheria is missing data but it's home to Pit River tribe for which we do have enrollment data

replace tribe_id=372 if strpos(Tribe, "yankton")==1
tab Tribe if tribe_id==372
replace tribe_id=373 if strpos(Tribe, "yavapai apache")==1
tab Tribe if tribe_id==373
replace tribe_id=374 if strpos(Tribe, "yavapai prescott")==1
replace tribe_id=374 if strpos(Tribe, "yavapai-prescott indian tribe")==1
tab Tribe if tribe_id==374
replace tribe_id=375 if strpos(Tribe, "yerington")==1
tab Tribe if tribe_id==375
replace tribe_id=376 if strpos(Tribe, "rumsey")==1
replace tribe_id=376 if strpos(Tribe, "yocha dehe")==1
tab Tribe if tribe_id==376

replace tribe_id=377 if strpos(Tribe, "yomba")==1
tab Tribe if tribe_id==377
replace tribe_id=378 if strpos(Tribe, "ysleta")==1
tab Tribe if tribe_id==378
replace tribe_id=379 if strpos(Tribe, "san manuel")==1
tab Tribe if tribe_id==379
replace tribe_id=380 if strpos(Tribe, "yurok")==1
replace tribe_id=380 if strpos(Tribe, "the yurok tribe")==1
tab Tribe if tribe_id==380
**I'm unsure about yurok alliance for northern california housing but I'll keep it
replace tribe_id=381 if strpos(Tribe, "zuni")==1
replace tribe_id=381 if strpos(Tribe, "pueblo of zuni")==1
tab Tribe if tribe_id==381
replace flag=1 if Tribe=="zuni public school district"
replace flag=1 if Tribe=="zuni housing authority"
**I'm unsure about zuni housing authority but I'll drop it


drop if flag==1

**Below I add some tribally controlled entities
**A useful link to check if a school is tribally operated: https://www.bie.edu/schools/directory/rock-point-community-school
**Here's also a full list of tribal schools: https://www.bia.gov/sites/default/files/dup/assets/as-ia/raca/pdf/idc008036.pdf

**School assignment rules:
**If a school is BIA-operated or tribally controlled, assign to a tribe on whose land it is located,
**unless the school serves multiple tribes. Need to distinguish between tribally controlled and BIA-operated schools later. 

replace tribe_id=207 if strpos(Tribe, "7c land and cattle, llc")==1
replace tribe_id=207 if strpos(Tribe, "7c land and cattle llc")==1
replace tribe_id=323 if strpos(Tribe, "te moak tribal western shoshone housing authority")==1
replace tribe_id=323 if strpos(Tribe, "temoak western shoshone law enforcement svcs public safety board")==1
replace tribe_id=327 if strpos(Tribe, "college of muscogee nation")==1
replace tribe_id=327 if strpos(Tribe, "college of the muscogee nation")==1
replace tribe_id=74 if strpos(Tribe, "little big horn college")==1 
replace tribe_id=74 if strpos(Tribe, "little big horn community college")==1 
replace tribe_id=192 if strpos(Tribe, "ramah navajo school board inc")==1
replace tribe_id=192 if strpos(Tribe, "ramah navajo school board, inc")==1
replace tribe_id=192 if strpos(Tribe, "ramah navajo chapter")==1
replace tribe_id=215 if strpos(Tribe, "indian township passamaquoddy school committee")==1
replace tribe_id=192 if strpos(Tribe, "nazlini community school")==1
replace tribe_id=192 if strpos(Tribe, "nazlini community school")==1
replace tribe_id=192 if strpos(Tribe, "rock point school inc")==1
replace tribe_id=192 if strpos(Tribe, "rock point school, incorporated")==1
replace tribe_id=192 if strpos(Tribe, "leupp school inc")==1
replace tribe_id=192 if strpos(Tribe, "leupp brdg sch board inc")==1
replace tribe_id=192 if strpos(Tribe, "lukachukai community school")==1
replace tribe_id=192 if strpos(Tribe, "na'neelzhiin ji'olta inc")==1
replace tribe_id=192 if strpos(Tribe, "na neelzhiin ji olta inc")==1
replace tribe_id=192 if strpos(Tribe, "naatsis'aan community school")==1
replace tribe_id=201 if strpos(Tribe, "little wound school board, inc.")==1
replace tribe_id=201 if strpos(Tribe, "little wound school")==1
replace tribe_id=112 if strpos(Tribe, "keams canyon elementary school")==1
replace tribe_id=312 if strpos(Tribe, "little eagle grant school")==1
replace tribe_id=312 if strpos(Tribe, "sitting bull school")==1
replace tribe_id=201 if strpos(Tribe, "loneman school")==1
replace tribe_id=112 if strpos(Tribe, "moencopi day school, inc.")==1
replace tribe_id=45 if strpos(Tribe, "takini school")==1
replace tribe_id=362 if strpos(Tribe, "theodore roosevelt school")==1
replace tribe_id=300 if strpos(Tribe, "tiospa zina tribal school")==1
replace tribe_id=300 if strpos(Tribe, "tiospa zina tribal school brd.")==1
replace tribe_id=192 if strpos(Tribe, "tse daa kaan chapter")==1
replace tribe_id=331 if strpos(Tribe, "twin buttes elementary school")==1
replace tribe_id=331 if strpos(Tribe, "twin buttes school district 37")==1
replace tribe_id=268 if strpos(Tribe, "sicangu owayawa oti")==1
replace tribe_id=331 if strpos(Tribe, "nueta hidatsa sahnish college")==1
replace tribe_id=246 if strpos(Tribe, "kha'p'o community school")==1
replace tribe_id=192 if strpos(Tribe, "kin dah lichi i olta school")==1
replace tribe_id=192 if strpos(Tribe, "pinon community school")==1
replace tribe_id=192 if strpos(Tribe, "pinon community school inc")==1
replace tribe_id=192 if strpos(Tribe, "rough rock school board, inc.")==1
replace tribe_id=192 if strpos(Tribe, "rough rock school board inc")==1
replace tribe_id=112 if strpos(Tribe, "second mesa day school")==1
replace tribe_id=192 if strpos(Tribe, "shiprock alternative schools")==1
replace tribe_id=192 if strpos(Tribe, "shiprock associated school inc")==1
replace tribe_id=372 if strpos(Tribe, "wagner community school")==1
replace tribe_id=372 if strpos(Tribe, "wagner school")==1
replace tribe_id=192 if strpos(Tribe, "wide ruins community school")==1
replace tribe_id=192 if strpos(Tribe, "wide ruins community school inc")==1
replace tribe_id=201 if strpos(Tribe, "wounded knee district school")==1
replace tribe_id=268 if strpos(Tribe, "sicangu wicoti awayankape corporation")==1
replace tribe_id=82 if strpos(Tribe, "joint programs - eastern shoshone tribe")==1
replace tribe_id=66 if strpos(Tribe, "yellowhawk tribal health center")==1
replace tribe_id=352 if strpos(Tribe, "white river construction")==1
replace tribe_id=199 if strpos(Tribe, "shoshone nation housing authority")==1
replace tribe_id=93 if strpos(Tribe, "aaniiih nakoda college")==1
replace tribe_id=120 if strpos(Tribe, "housing authority of the iowa tribe of kansas & nebraska inc")==1
replace tribe_id=121 if strpos(Tribe, "housing authority of the iowa tribe of oklahoma")==1
replace tribe_id=138 if strpos(Tribe, "housing authority of the kickapoo tribe of oklahoma")==1
replace tribe_id=228 if strpos(Tribe, "housing authority of the ponca tribe of indians of oklahoma")==1
replace tribe_id=268 if strpos(Tribe, "sinte gleska university")==1   
replace tribe_id=192 if strpos(Tribe, "black mesa community school")==1  
replace tribe_id=100 if strpos(Tribe, "blackwater community school")==1  
replace tribe_id=250 if strpos(Tribe, "chief leschi schools")==1  
replace tribe_id=250 if strpos(Tribe, "chief leschi school, inc.")==1  
replace tribe_id=221 if strpos(Tribe, "indian island penobscot school committee")==1  
replace tribe_id=192 if strpos(Tribe, "chinle boarding school, inc.")==1   
replace tribe_id=102 if strpos(Tribe, "chippewa ottawa resource authority")==1  
replace tribe_id=102 if strpos(Tribe, "chippewa ottawa resource autho")==1  
replace tribe_id=102 if strpos(Tribe, "chippewa ottawa resources authority")==1  
replace tribe_id=112 if strpos(Tribe, "hotevilla-bacavi community school district")==1 
replace tribe_id=112 if strpos(Tribe, "hotevilla-bacavi community sch")==1 
replace tribe_id=192 if strpos(Tribe, "greasewood springs community school, inc.")==1  
replace tribe_id=192 if strpos(Tribe, "greasewood sprgs comm school")==1  
replace tribe_id=192 if strpos(Tribe, "hanaa'dli community school dormitory, in.")==1  
replace tribe_id=192 if strpos(Tribe, "hanaa'dli community school dormitory, inc.")==1  
replace tribe_id=109 if strpos(Tribe, "h0-chunk nation execut ofcs")==1   
replace tribe_id=222 if strpos(Tribe, "ha of the peoria tribe of indians")==1 
replace tribe_id=93 if strpos(Tribe, "ft belknap indian comm")==1
replace tribe_id=331 if strpos(Tribe, "ft berthold community college")==1
replace tribe_id=329 if strpos(Tribe, "ha of the seminole nation")==1
replace tribe_id=163 if strpos(Tribe, "northwest indian college foundation")==1 
replace tribe_id=343 if strpos(Tribe, "trenton indian service area development corporation")==1 
replace tribe_id=343 if strpos(Tribe, "trenton indian services area")==1 
replace tribe_id=343 if strpos(Tribe, "trenton indian housing authority")==1 
replace tribe_id=343 if strpos(Tribe, "trenton indian service area")==1 
replace tribe_id=49 if strpos(Tribe, "stone child college corporation")==1
replace tribe_id=209 if strpos(Tribe, "utah paiute tribal housing authority, inc.")==1
replace tribe_id=209 if strpos(Tribe, "utah paiute ha")==1
replace tribe_id=209 if strpos(Tribe, "utah paiute tribal housing authority")==1
**for the three entities above, I wasn't 100% sure between tribe_id=118 and tribe_id=209
replace tribe_id=268 if strpos(Tribe, "sicangu oyate ho inc")==1
replace tribe_id=345 if strpos(Tribe, "29 palms enterprises corp")==1
replace tribe_id=137 if strpos(Tribe, "kickapoo nation school")==1 
replace tribe_id=148 if strpos(Tribe, "chippewa ottawa resources authority")==1 
replace tribe_id=192 if strpos(Tribe, "alamo navajo school board, inc., the")==1   
replace tribe_id=308 if strpos(Tribe, "cankdeska cikana community college")==1   
replace tribe_id=308 if strpos(Tribe, "cankdeska cikana community")==1   
replace tribe_id=201 if strpos(Tribe, "porcupine local district")==1 
replace tribe_id=201 if strpos(Tribe, "porcupine school")==1 
replace tribe_id=192 if strpos(Tribe, "richfield residential hall school board, inc.")==1 
replace tribe_id=192 if strpos(Tribe, "chilchinbeto community school inc.")==1 
replace tribe_id=192 if strpos(Tribe, "greasewood springs cmnty schl")==1 
replace tribe_id=197 if strpos(Tribe, "chief dull knife college, inc")==1 
replace tribe_id=192 if strpos(Tribe, "dzilth-na-o-dith-hle school board of education, inc.")==1 
replace tribe_id=331 if strpos(Tribe, "mandaree school district 36")==1 
replace tribe_id=48 if strpos(Tribe, "mathiesen memorial health clinic")==1 
replace tribe_id=372 if strpos(Tribe, "marty indian school board, inc.")==1 
replace tribe_id=372 if strpos(Tribe, "marty indian school")==1 
replace tribe_id=192 if strpos(Tribe, "hunters point boarding school")==1 
replace tribe_id=312 if strpos(Tribe, "sitting bull college")==1 
replace tribe_id=192 if strpos(Tribe, "tiisyaakin residential hall, inc.")==1 
replace tribe_id=192 if strpos(Tribe, "shonto preparatory school district")==1
replace tribe_id=192 if strpos(Tribe, "shonto governing board of")==1
replace tribe_id=192 if strpos(Tribe, "tohajiilee community school board of education inc")==1 
replace tribe_id=192 if strpos(Tribe, "winslow residential hall, inc.")==1 
replace tribe_id=300 if strpos(Tribe, "enemy swim day school")==1 
replace tribe_id=192 if strpos(Tribe, "winslow residential hall")==1 
replace tribe_id=364 if strpos(Tribe, "wcd wic program")==1 
replace tribe_id=364 if strpos(Tribe, "wcd enterprises, ok")==1 
replace tribe_id=364 if strpos(Tribe, "wcd enterprises  ok")==1 
replace tribe_id=192 if strpos(Tribe, "ch'ooshgai community school board of education, inc.")==1 
replace tribe_id=268 if strpos(Tribe, "sicangu child & family services")==1 
replace tribe_id=268 if strpos(Tribe, "sicangu child and family serv")==1 
replace tribe_id=215 if strpos(Tribe, "indian township health centre")==1 
replace tribe_id=215 if strpos(Tribe, "indian township passamaquoddy development agency")==1 
replace tribe_id=201 if strpos(Tribe, "crazy horse school")==1  
replace tribe_id=192 if strpos(Tribe, "canoncito band of navajo health center, inc")==1 
replace tribe_id=192 if strpos(Tribe, "dine bi olta school board association inc")==1 
replace tribe_id=192 if strpos(Tribe, "dine bi olta school board assc")==1 
replace tribe_id=192 if strpos(Tribe, "dilcon community school, inc.")==1 
replace tribe_id=192 if strpos(Tribe, "little singer community school board inc")==1 
replace tribe_id=192 if strpos(Tribe, "little singer community school")==1 
replace tribe_id=201 if strpos(Tribe, "american horse school")==1 
replace tribe_id=333 if strpos(Tribe, "san lucy district")==1 
replace tribe_id=100 if strpos(Tribe, "casa blanca community school, inc.")==1 
replace tribe_id=112 if strpos(Tribe, "first mesa elementary school")==1 
replace tribe_id=268 if strpos(Tribe, "tribal land enterprises")==1 
replace tribe_id=49 if strpos(Tribe, "dry fork farms")==1 
replace tribe_id=234 if strpos(Tribe, "haaku community academy")==1
replace tribe_id=109 if strpos(Tribe, "ho chunk community development corp")==1 
replace tribe_id=214 if strpos(Tribe, "rolling hills clinic")==1 
replace tribe_id=138 if strpos(Tribe, "kickapoo head start inc")==1
replace tribe_id=20 if strpos(Tribe, "konocti vista casino")==1
replace tribe_id=362 if strpos(Tribe, "cibecue community education board, inc.")==1
replace tribe_id=362 if strpos(Tribe, "apache behavioral health services inc")==1
replace tribe_id=45 if strpos(Tribe, "crst telephone authority")==1
replace tribe_id=343 if strpos(Tribe, "ojibwa indian school")==1
replace tribe_id=343 if strpos(Tribe, "ojibwa tribal school inc")==1
replace tribe_id=272 if Tribe=="sac and fox settlement school"
replace tribe_id=96 if Tribe=="ft mcdermitt stockmens association inc"
**I'm not 100% sure about the one above as it no longer exists but I'll keep it
replace tribe_id=274 if Tribe=="akwesasne housing authority"
replace tribe_id=274 if Tribe=="akwesasne indian housing authority"
replace tribe_id=98 if Tribe=="aha macav housing entity"
replace tribe_id=98 if Tribe=="aha macav power service"
replace tribe_id=192 if Tribe=="alamo navajo school board inc"
replace tribe_id=192 if Tribe=="alamo navajo school board"
replace tribe_id=201 if Tribe=="cangleska, inc."
replace tribe_id=192 if Tribe=="dibe yazhi habitiin olta, inc"
replace tribe_id=100 if Tribe=="casa blanca comm sch inc"
replace tribe_id=197 if Tribe=="chief dull knife college"
replace tribe_id=192 if Tribe=="dine college"
replace tribe_id=192 if Tribe=="burnham chapter of the navajo nation"
replace tribe_id=192 if Tribe=="chinle chapter"
replace tribe_id=192 if Tribe=="chilchinbeto community school"
replace tribe_id=362 if Tribe=="cibecue community educ brd inc"
replace tribe_id=151 if Tribe=="chief-bug o nay ge shig school"
replace tribe_id=380 if Tribe=="coast indian community of"
replace tribe_id=361 if Tribe=="circle of life survival school"
replace tribe_id=192 if Tribe=="dzilth-na-o-dith-hle community"
replace tribe_id=196 if Tribe=="arapahoe ranch"
replace tribe_id=192 if Tribe=="chuska school board of"
replace tribe_id=192 if Tribe=="dilcon boarding school"
replace tribe_id=192 if Tribe=="borrego pass school inc"
replace tribe_id=98 if Tribe=="avi kwa ame farms"
replace tribe_id=192 if Tribe=="aztec high school dormitory"
replace tribe_id=22 if Tribe=="browning school district #9"
replace tribe_id=58 if Tribe=="dixon school district 9"
replace tribe_id=333 if Tribe=="gu achi livestock associat"
replace tribe_id=333 if Tribe=="gu achi livestock association"
replace tribe_id=333 if Tribe=="gu-achi district office"
replace tribe_id=192 if Tribe=="huerfano chapter of the navajo nation"
replace tribe_id=192 if Tribe=="hanaa'dli community school/"
replace tribe_id=192 if Tribe=="holbrook dormitory, inc."
replace tribe_id=111 if Tribe=="hoopa tribal forestry department"
replace tribe_id=192 if Tribe=="hardrock chapter"
replace tribe_id=100 if Tribe=="gila crossing community school"
replace tribe_id=112 if Tribe=="moenkopi senior center"
replace tribe_id=112 if Tribe=="moencopi day school"
replace tribe_id=112 if Tribe=="moenkopi developers corporation, incorporated"
replace tribe_id=155 if Tribe=="ltbb of odawa indians"
replace tribe_id=192 if Tribe=="nageezi chapter of the navajo nation"
replace tribe_id=151 if Tribe=="leech band of ojibwe"
replace tribe_id=366 if Tribe=="little priest tribal college"
replace tribe_id=201 if Tribe=="lakota oyate wakanyeja owicakiyapi (lowo)"
replace tribe_id=192 if Tribe=="kin dah lichi'i olta"
replace tribe_id=68 if Tribe=="mithihkwuh economic development corp"
replace tribe_id=70 if Tribe=="k-bar ranches corp"
replace tribe_id=114 if Tribe=="maliseets indian housing authority"
replace tribe_id=175 if Tribe=="micmac health department"
replace tribe_id=326 if Tribe=="jones academy"
replace tribe_id=192 if Tribe=="torreon chapter of the navajo nation"
replace tribe_id=342 if Tribe=="toulumne me-wuk housing authority"
replace tribe_id=192 if Tribe=="tohajiilee"
replace tribe_id=192 if Tribe=="to'hajiilee community school"
replace tribe_id=192 if Tribe=="pueblo pintado chapter of the navajo nation"
replace tribe_id=192 if Tribe=="ramah navajo community enterprises in"
replace tribe_id=70 if Tribe=="uidc k-bar ranches division"
replace tribe_id=192 if Tribe=="steamboat chapter"
replace tribe_id=312 if Tribe=="srst rock creek district"
replace tribe_id=275 if Tribe=="srpmic community school"
replace tribe_id=92 if Tribe=="wisconsin potawatomi housing authority"
replace tribe_id=192 if Tribe=="whitehorse lake chapter of the navajo nation"
replace tribe_id=299 if Tribe=="western shoshone-paiute livestock association"
replace tribe_id=300 if Tribe=="wacanga" //this shelter is tribally affiliated
replace tribe_id=192 if Tribe=="tse si ani chapter"
replace tribe_id=378 if Tribe=="tigua community development corporation"
replace tribe_id=39 if Tribe=="suh'dutsing technologies, llc"
replace tribe_id=333 if Tribe=="san xavier district"
replace tribe_id=333 if Tribe=="san xavier district of the tohono o'odham nat"
replace tribe_id=238 if Tribe=="sedillo cattle assoc"
replace tribe_id=238 if Tribe=="sedillo cattle association"
replace tribe_id=272 if Tribe=="sac & fox ha"
replace tribe_id=271 if Tribe=="sac & fox housing authority inc"
replace tribe_id=312 if Tribe=="pretty bird woman house, inc" //this shelter is tribally affiliated 
replace tribe_id=192 if Tribe=="pine springs district 4"
replace tribe_id=201 if Tribe=="pine ridge school"
replace tribe_id=192 if Tribe=="ojo encino chapter of the navajo nation"
replace tribe_id=204 if Tribe=="onsin oneida tribe of wisc"
replace tribe_id=312 if Tribe=="rock creek grant school"
replace tribe_id=192 if Tribe=="richfield residential hall inc"
replace tribe_id=304 if Tribe=="noli school"
replace tribe_id=304 if Tribe=="noli school - soboba tribe"
replace tribe_id=353 if Tribe=="ute ute gwaiti paiute"
replace tribe_id=351 if Tribe=="ute tribe water settlement"
replace tribe_id=352 if Tribe=="ute indian tribally designated housing entity"
replace tribe_id=352 if Tribe=="ute mt ute tribe weeminuche construction au."
replace tribe_id=351 if Tribe=="ute enterprises, llc"
replace tribe_id=49 if Tribe=="stone child college"
replace tribe_id=49 if Tribe=="stone child community college"
replace tribe_id=22 if Tribe=="siyeh communications"
replace tribe_id=22 if Tribe=="siyeh communications co"
replace tribe_id=229 if Tribe=="northern ponca housing authority"
replace tribe_id=179 if Tribe=="nay ah shing school"
replace tribe_id=192 if Tribe=="nenahnezad"
replace tribe_id=192 if Tribe=="nenahnezad bureau of indian affairs community schools"
replace tribe_id=192 if Tribe=="kayenta chapter"
replace tribe_id=192 if Tribe=="dilkon chapter"
replace tribe_id=277 if Tribe=="triplet mountain communications, inc"
replace tribe_id=100 if Tribe=="tribal employment rights office inc"
replace tribe_id=192 if Tribe=="kinteel residential campus, inc."
replace tribe_id=364 if Tribe=="wichita housing authority"
replace tribe_id=192 if Tribe=="counselor chapter of the navajo nation"


**the following entities should NOT be assigned a tribe_id (I googled if ambiguous):
drop if Tribe=="overton county schools"
drop if Tribe=="kanu o ka aina charter school"
drop if Tribe=="anansi charter school"
drop if Tribe=="anadarko public schools"
drop if Tribe=="four corners school of outdoor education inc., the"
drop if Tribe=="sunny day child care & preschool, inc."
drop if Tribe=="bonesteel-fairfax school 26-5"
drop if Tribe=="carnegie public schools"
drop if Tribe=="branson reorganized school district 82"
drop if Tribe=="chesterfield county school district"
drop if Tribe=="flat rock-hawcreek school corp"
drop if Tribe=="fort cobb braxton school"
drop if Tribe=="new haven unif school district"
drop if Tribe=="albuquerque public school district"
drop if Tribe=="boswell school district i 1"
drop if Tribe=="bright futures daycare and preschool,inc"
drop if Tribe=="west iron county    public schools"
drop if Tribe=="west bolivar consolidated school district"
drop if Tribe=="spring branch independent school district (inc)"
drop if Tribe=="corning community school district"
drop if Tribe=="chawanakee joint school dist"
drop if Tribe=="ballard high school"
drop if Tribe=="crowley county school district re-1-j"
drop if Tribe=="coahoma county school district"
drop if Tribe=="brockton public schools"
drop if Tribe=="neighborhood schoolhouse of brattleboro"
drop if Tribe=="commerce public schools"
drop if Tribe=="bedford community school dist"
drop if Tribe=="cache public schools"
drop if Tribe=="cutler orosi joint unified school district"
drop if Tribe=="lubbock-cooper independent school district"
drop if Tribe=="dorchester county school district 4 inc"
drop if Tribe=="east union community school district"
drop if Tribe=="enosburgh town school district"
drop if Tribe=="beaverton rural school district"
drop if Tribe=="south kingstown public schools"
drop if Tribe=="covert public school district"
drop if Tribe=="laquey school district of pulaski county"
drop if Tribe=="cache public schools"
drop if Tribe=="oklahoma city public schools"
drop if Tribe=="four directions development corp"
drop if Tribe=="four bands community fund inc"
drop if Tribe=="haskell foundation"
drop if Tribe=="state center community college district"
drop if Tribe=="fort plain village office"
drop if Tribe=="sioux falls housing and redevelopment commission"
drop if Tribe=="richmond redevelopment and housing authority"
drop if Tribe=="monticello, village of"
drop if Tribe=="hammond housing athority"
drop if Tribe=="dupage housing authority"
drop if Tribe=="dover housing authority"
drop if Tribe=="ocala housing authority"
drop if Tribe=="nw georgia housing authority"
drop if Tribe=="gloversville housing authority"
drop if Tribe=="galveston housing authority"
drop if Tribe=="sacramnto hsing rdvlpment agency"
drop if Tribe=="rowan county housing authority"
drop if Tribe=="western piedmont council of governments"
drop if Tribe=="donnelly college"
drop if Tribe=="deep east texas council of governments"
drop if Tribe=="bessemer housing authority"
drop if Tribe=="boca raton housing authority"
drop if Tribe=="carroll county commissioners of"
drop if Tribe=="chelmsford housing authority"
drop if Tribe=="home forward development enterprises"
drop if Tribe=="waadookodaading ojibwe language institute, inc."
drop if Tribe=="edith k. kanaka'ole foundation"
drop if Tribe=="indian child & family services"
drop if Tribe=="mo-ark water company"
drop if Tribe=="middlesex community college"
drop if Tribe=="kawerak inc"
drop if Tribe=="dough mountain association" //not sure about this one, couldn't find much
drop if Tribe=="wopanaak language and cultural weetyoo, inc."
drop if Tribe=="tribal fishco llc"
drop if Tribe=="sanford housing authority"
drop if Tribe=="vermont state housing authority"
drop if Tribe=="nevada urban indians inc."
drop if Tribe=="worcester housing authority"
drop if Tribe=="rochester housing authority"
drop if Tribe=="st louis housing authority"
drop if Tribe=="wyoming housing commission"
drop if Tribe=="san bernardino county indian"
drop if Tribe=="syracuse housing authority"
drop if Tribe=="developing innovation in navajo education inc"
drop if Tribe=="community environmental center inc"
drop if Tribe=="chaco heritage tribal association"
drop if Tribe=="center school inc"
drop if Tribe=="shoshone & arapaho minerals compliance"
drop if Tribe=="norfolk redevelopment housing authority"
drop if Tribe=="new lima public schools"
drop if Tribe=="siskiyou joint community college district"
drop if Tribe=="sierra plumas joint unified school district"
drop if Tribe=="sierra unified school district"
drop if Tribe=="stockton unified school district"
drop if Tribe=="shoshone crusher" //not sure about this one, couldn't find much
drop if Tribe=="strother public school"
drop if Tribe=="north wind site services, llc"
drop if Tribe=="naytahwaush community foundation" //not sure about this one, couldn't find much 
drop if Tribe=="northwest indian fisheries com"
drop if Tribe=="ncai fund"
drop if Tribe=="n. a. t. i. v. e. project, the"
drop if Tribe=="napa housing authority"
drop if Tribe=="sia inc"
drop if Tribe=="nampa housing authority inc"
drop if Tribe=="norman public schools"
drop if Tribe=="northern circle indian housing authority"
drop if Tribe=="new destiny center inc"
drop if Tribe=="new ecology inc"
drop if Tribe=="native village of kotzebue"
drop if Tribe=="skagit system cooperative"
drop if Tribe=="stoddar development found"
drop if Tribe=="oakville school district 400"
drop if Tribe=="oaks mission sch dist i-5"
drop if Tribe=="ocean beach school district"
drop if Tribe=="northwoods niijii enterprise community, inc."
drop if Tribe=="northwest indian college" //this is a tribal college that appears to serve Native Americans from multiple tribes
drop if Tribe=="okanogan employees childcare association"
drop if Tribe=="oceti wakan (sacrid fireplace)"
drop if Tribe=="vermillion school distr 13-1"
drop if Tribe=="villisca community school district"
drop if Tribe=="vance-granville community college"
drop if Tribe=="niijii capital partners inc"
drop if Tribe=="ngchesar state government"
drop if Tribe=="ngeremlengui state government"
drop if Tribe=="noah's ark daycare center  inc"
drop if Tribe=="noah's ark daycare center, inc"
drop if Tribe=="noah's ark day carecenter inc"
drop if Tribe=="nizi puh wah sin inc"
drop if Tribe=="richland school district 2"
drop if Tribe=="sevier school district inc"
drop if Tribe=="region 10 tribal operations committee consortium"
drop if Tribe=="otis school district r-3"
drop if Tribe=="rosemary's daycare & learning center"
drop if Tribe=="onekama consolidated schools"
drop if Tribe=="onaway area community schools"
drop if Tribe=="roseland school district"
drop if Tribe=="sequoyah fund inc"
drop if Tribe=="our lady of mercy catholic high school"
drop if Tribe=="republic-michigamme school district"
drop if Tribe=="renaissance charter school"
drop if Tribe=="reservation transportation authority"
drop if Tribe=="oweesta corp"
drop if Tribe=="owens valley board of trustees"
drop if Tribe=="owens valley indian housing authority"
drop if Tribe=="passaic county community college"
drop if Tribe=="paul smiths college of arts and sciences"
drop if Tribe=="phoenix indian center"
drop if Tribe=="pestomuhkati mawuhkah"
drop if Tribe=="papahana kuaola"
drop if Tribe=="reef-sunset unified school district"
drop if Tribe=="prestera center for mental health services, inc"
drop if Tribe=="pomeroy-palmer community school"
drop if Tribe=="pohnpei st. gvt doe"
drop if Tribe=="pohnpei state government"
drop if Tribe=="pleasant grove public school"
drop if Tribe=="red feather development group"
drop if Tribe=="primeros pasos inc"
drop if Tribe=="salt creek rural road orginization"
drop if Tribe=="salt creek joint powers board"
drop if Tribe=="seminole" //primary place of performance is in FL but the city doesn't match at all
drop if Tribe=="sasakwa schools i-10"
drop if Tribe=="sandpoint charter school, inc."
drop if Tribe=="san luis rey indian water authority"
drop if Tribe=="saint paul's college"
drop if Tribe=="seldovia village tribe"
drop if Tribe=="tarrant county college district"
drop if Tribe=="territorial administration on aging"
drop if Tribe=="tbd"
drop if Tribe=="tafesilafai"
drop if Tribe=="sun'aq tribe of kodiak"
drop if Tribe=="tamworth pre-school, inc."
drop if Tribe=="summerville union high schools"
drop if Tribe=="sunshine services, inc."
drop if Tribe=="sunrise growers, inc."
drop if Tribe=="youngdeer inc"
drop if Tribe=="yakaama indian education & development inc"
drop if Tribe=="wabash community unit school district 348"
drop if Tribe=="yosemite community college district"
drop if Tribe=="wisdom of the elders inc"
drop if Tribe=="verden public school"
drop if Tribe=="varnum public school"
drop if Tribe=="vctc"
drop if Tribe=="the learning center at the euchee butterfly farm inc"
drop if Tribe=="tuba city high school board in"
drop if Tribe=="three creek elementary joint school district 416"
drop if Tribe=="theodore jamerson elem. school"
drop if Tribe=="the lakota fund inc" //I'm not 100% sure about this one
drop if Tribe=="texas native health"
drop if Tribe=="west sioux community school district"
drop if Tribe=="western heights pblc schl i041"
drop if Tribe=="west valley-mission community college district"
drop if Tribe=="white shield public school dis"
drop if Tribe=="south central school district"
drop if Tribe=="south brown county usd #430"
drop if Tribe=="st george tanaq corp"
drop if Tribe=="south pacific academy, inc."
drop if Tribe=="south bend housing authority"
drop if Tribe=="south texas college"
drop if Tribe=="spotted eagle inc"
drop if Tribe=="st bar ranch"
drop if Tribe=="st stephens indian school"
drop if Tribe=="wind river tribal college"
drop if Tribe=="turquoise springs livestock association"
drop if Tribe=="turkey ford school"
drop if Tribe=="tzicatl community development corporation"
drop if Tribe=="tse hdeeshgiish enterprise"
drop if Tribe=="rambo committee inc"
drop if Tribe=="quitman county school district"
drop if Tribe=="red cloud indian school, inc."
drop if Tribe=="putnam city schools"
drop if Tribe=="proworks inc"
drop if Tribe=="red-spectrum communications"
drop if Tribe=="red rocks community college"
drop if Tribe=="tolani lake enterprises inc"
drop if Tribe=="todd county school dist 66-1" //this district is entirely or almost entirely on the Rosebud reservation
drop if Tribe=="mound bayou com hos& delta health cen"
drop if Tribe=="lawton service unit, lawton phs indian health hospital"
drop if Tribe=="macomb intermediate school district"
drop if Tribe=="missoula housing authority"
drop if Tribe=="missoula community health services"
drop if Tribe=="mtn. view-gotebo schools"
drop if Tribe=="los banos unified school district"
drop if Tribe=="justice school c054"
drop if Tribe=="lyons central school district"
drop if Tribe=="lawrence usd #497"
drop if Tribe=="lisbon exempted village school district"
drop if Tribe=="lisbon ex village school"
drop if Tribe=="lawrence public schools"
drop if Tribe=="lometa independent school district"
drop if Tribe=="mountain projects, inc."
drop if Tribe=="keyes union school district"
drop if Tribe=="keene housing authority"
drop if Tribe=="mccleary elem school dist 65"
drop if Tribe=="marysville joint unified school district"
drop if Tribe=="marysville unified school district 364"
drop if Tribe=="krayola learning academy, inc."
drop if Tribe=="jeehdeez'a academy incorporate"
drop if Tribe=="la clinica del pueblo"
drop if Tribe=="malama learning center"
drop if Tribe=="manumalo baptist school"
drop if Tribe=="munday consolidated independent school district"
drop if Tribe=="montano cattle assoc"
drop if Tribe=="lakeside union school district"
drop if Tribe=="kavilco inc"
drop if Tribe=="lindsay unified school district"
drop if Tribe=="keiki 'o ka 'aina preschool, inc."
drop if Tribe=="kanu o ka aina learning ohana"
drop if Tribe=="la red health center, inc."
drop if Tribe=="mount ayr community school district"
drop if Tribe=="na nizhoozhi center inc"
drop if Tribe=="nanizhoozhi center inc."
drop if Tribe=="kanu o ka aina ncpcs"
drop if Tribe=="lookeba-sickles public school"
drop if Tribe=="moore public schools"
drop if Tribe=="moseley public schools"
drop if Tribe=="martins ferry city school district"
drop if Tribe=="mid-del schools"
drop if Tribe=="kipahulu ohana, inc."
drop if Tribe=="kipp: delta  inc."
drop if Tribe=="little star montessori school"
drop if Tribe=="naihc"
drop if Tribe=="merced union high"
drop if Tribe=="ke aupuni lokahi, inc."
drop if Tribe=="molokai ohana health care, inc"
drop if Tribe=="moloka`i land trust"
drop if Tribe=="lamoni community school district"
drop if Tribe=="metlakatla indian community"
drop if Tribe=="muldrow cherokee communit"
drop if Tribe=="mound bayou public school systems"
drop if Tribe=="lake wales charter schools inc"
drop if Tribe=="lockheed martin"
drop if Tribe=="lockheed martin services, inc."
drop if Tribe=="lockheed martin services, llc"
drop if Tribe=="lockheed martin svcs"
drop if Tribe=="na puuwai"
drop if Tribe=="kenaitze indian tribe"
drop if Tribe=="ketchikan indian community"
drop if Tribe=="k u t e inc"
drop if Tribe=="long beach city college"
drop if Tribe=="kirtland community college"
drop if Tribe=="mississippi delta community college"
drop if Tribe=="murray state college"
drop if Tribe=="luna community college"
drop if Tribe=="luzerne county community college"
drop if Tribe=="midland college"
drop if Tribe=="juanita college"
drop if Tribe=="michigan state housing development authority"
drop if Tribe=="memphis housing authority"
drop if Tribe=="mcgehee housing authority"
drop if Tribe=="mechanicville housing authority"
drop if Tribe=="mankato housing & economic development authority"
drop if Tribe=="maine state housing authority"
drop if Tribe=="maine indian education"
drop if Tribe=="greenville elementary school"
drop if Tribe=="great plains tribal water alliance, inc."
drop if Tribe=="grand coulee dam school district"
drop if Tribe=="georgia gwinnett college"
drop if Tribe=="geronimo public schools"
drop if Tribe=="howard-winneshiek community school district"
drop if Tribe=="huerfano school district number re-1"
drop if Tribe=="independent school dist # 625"
drop if Tribe=="hayes center school district 79"
drop if Tribe=="heber elementary school district"
drop if Tribe=="houghton lake community schools"
drop if Tribe=="hooper irrigation company"
drop if Tribe=="holland town school district"
drop if Tribe=="hesperia community school district"
drop if Tribe=="helena indian alliance"
drop if Tribe=="heart of earth center" //can't find this organization at all
drop if Tribe=="idalia school district rj-3"
drop if Tribe=="hooulu-lahui"
drop if Tribe=="delaware division of small business"
drop if Tribe=="deer / mt. judea school district"
drop if Tribe=="edgemont school district 23-1"
drop if Tribe=="central decatur community school distric"
drop if Tribe=="brighton town school district"
drop if Tribe=="el tejon unified school district"
drop if Tribe=="edmond public schools isd #12"
drop if Tribe=="central union elementary sch d"
drop if Tribe=="central union elementary school district"
drop if Tribe=="canyon owyhee school service agency"
drop if Tribe=="consumer and market insights, llc"
drop if Tribe=="el reno public schools"
drop if Tribe=="el reno public school system district office"
drop if Tribe=="cyril public school"
drop if Tribe=="brazos valley council of governments"
drop if Tribe=="dine be' iina, inc."
drop if Tribe=="board of regents southwestern indian polytechnic institute"
drop if Tribe=="toiyabe indian health project, inc."
drop if Tribe=="k'ima:w medical center"
drop if Tribe=="konawa public school"
drop if Tribe=="haskill indian nations university"
drop if Tribe=="wa he lut indian school"
drop if Tribe=="wewoka public school i-002"
drop if Tribe=="wahpeton indian sch brd inc"
drop if Tribe=="white river school dist 47-1"
drop if Tribe=="great lakes community action partnership"
drop if Tribe=="great lakes environmental plan"
drop if Tribe=="great lakes indian fish"
drop if Tribe=="great lakes indian fish & wildlife commission"
drop if Tribe=="haudenosaunee environmental ta"
drop if Tribe=="haudenosaunee environmental task force"
drop if Tribe=="passamaquoddy wild blueberry company"
drop if Tribe=="passamaquoddy child development center"
drop if Tribe=="nek-cap inc"
drop if Tribe=="utah navajo health system, inc."
drop if Tribe=="united tribes technical colleg"
drop if Tribe=="winslow indian health care center"
drop if Tribe=="kodiak area native association"
drop if Tribe=="kohe malamalama o kanaloa protect kahoolawe fund"
drop if Tribe=="rocky mountain tribal leaders council"
drop if Tribe=="white river health system, inc."
drop if Tribe=="white river regional housing authority"
drop if Tribe=="united tribes technical college"
drop if Tribe=="california rural indian health board, inc."
drop if Tribe=="benewah medical center"
drop if Tribe=="american indian alaska native tourism association"
drop if Tribe=="association of american indian physicians, inc."
drop if Tribe=="central oklahoma american indian health council, inc."
drop if Tribe=="great lakes inter-tribal council, inc."
drop if Tribe=="great plains tribal leaders health board"
drop if Tribe=="lake county tribal health consortium, inc."
drop if Tribe=="indian nations university"
drop if Tribe=="institute of american indian arts"
drop if Tribe=="eastern washington university"
drop if Tribe=="eight northern indian pueblos council inc"
drop if Tribe=="housing authority of baltimore city"
drop if Tribe=="housing authority of bexar county"
drop if Tribe=="housing authority of city of everett"
drop if Tribe=="housing authority of city of fort lauderdale"
drop if Tribe=="housing opportunities commission of montgomery county"
drop if Tribe=="housing authority of city of evansville"
drop if Tribe=="housing authority of city of frederi"
drop if Tribe=="housing authority of the city of charleston"
drop if Tribe=="housing authority of the city of college park"
drop if Tribe=="housing authority of the city of north little rock arkansas"
drop if Tribe=="housing authority of the city of oakland, california"
drop if Tribe=="housing authority of the city of pine bluff"
drop if Tribe=="housing authority of the city of pittsburgh"
drop if Tribe=="the housing authority of the city of winston-salem"
drop if Tribe=="the housing authority of the county of dane, wisconsin"
drop if Tribe=="riverside-san bernardino county indian health, inc."
drop if Tribe=="saint charles, county of"
drop if Tribe=="santa fe, county of"
drop if Tribe=="southern california tribal chairmens association"
drop if Tribe=="upper columbia united tribes"
drop if Tribe=="south puget intertribal planning agency"
drop if Tribe=="national indian women's health resource center"
drop if Tribe=="southwestern indian polytechnic institute"
drop if Tribe=="five sandoval indian pueblos inc"
drop if Tribe=="intertribal agriculture counci"
drop if Tribe=="intertribal agriculture council"
drop if Tribe=="national indian health board"
drop if Tribe=="national indian education association"
drop if Tribe=="institute for native pacific education and culture"
drop if Tribe=="wind river inter-tribal council"
drop if Tribe=="coharie intra tribal council inc"
drop if Tribe=="department of aging california"
drop if Tribe=="department of education"
drop if Tribe=="department of education arizona"
drop if Tribe=="arkansas telephone company, inc."
drop if Tribe=="arlington housing authority"
drop if Tribe=="atlanta regional commission"
drop if Tribe=="atlantic city housing authority and urban redevelopment agency"
drop if Tribe=="small tribes organization of western was"
drop if Tribe=="housing authority of city of muskoge "
drop if Tribe=="housing authority of city of orange "
drop if Tribe=="indian health board of minneapolis inc"
drop if Tribe=="intertribal council of alabama"
drop if Tribe=="northern california indian development council inc"
drop if Tribe=="northwest washington indian health board"
drop if Tribe=="american institute of indian studie"
drop if Tribe=="columbia river inter-tribal fish commision"
drop if Tribe=="native american fish & wildlife society"
drop if Tribe=="affiliated tribes of northwest indians"
drop if Tribe=="affiliated tribes of northwest indians economic development corporation"
drop if Tribe=="fairfax county virginia"
drop if Tribe=="fairfield metropolitan housing authority"
drop if Tribe=="indian health council, inc"
drop if Tribe=="indian health council inc"
drop if Tribe=="indian nations conservation alliance"
drop if Tribe=="university of illinois"
drop if Tribe=="tuba city regional health care corporation"
drop if Tribe=="the institute for indian development inc"
drop if Tribe=="oregon child development coalition"
drop if Tribe=="native american family services, inc"
drop if Tribe=="native american family services, inc."
drop if Tribe=="wisconsin tribal conservation advisory council, inc."
drop if Tribe=="southern colorado community action agency, inc."
drop if Tribe=="northern valley indian health, inc."
drop if Tribe=="american indian higher education consortium"
drop if Tribe=="american samoa medical center authority"
drop if Tribe=="american samoa government"
drop if Tribe=="california indian manpower consortium inc"
drop if Tribe=="san diego association of governments"
drop if Tribe=="south dakota urban indian health, inc"
drop if Tribe=="northern plains intertribal court of appeals"
drop if Tribe=="northwest indian fisheries commission"
drop if Tribe=="northwest portland area indian health board"
drop if Tribe=="sierra tribal consortium inc"
drop if Tribe=="southern indian health council"
drop if Tribe=="healing lodge of the seven nations,the"
drop if Tribe=="housing & community development, md dept of"
drop if Tribe=="native american disability law center inc"
drop if Tribe=="nebraska urban indian health coalition, inc."
drop if Tribe=="lake county citizens committee on indian affairs"
drop if Tribe=="northwest intertribal court system"
drop if Tribe=="northwestern indiana regional planning c"
drop if Tribe=="native american environmental protection"
drop if Tribe=="network for oregon affordable housing"
drop if Tribe=="northeastern tribal health system"
drop if Tribe=="consolidated tribal health project, inc."
drop if Tribe=="cook inlet tribal council inc"
drop if Tribe=="housing authority of washington county"
drop if Tribe=="native americans for community action inc"
drop if Tribe=="the cherokee boys club inc"
drop if Tribe=="albuquerque area indian health board inc"
drop if Tribe=="owens valley career development center"
drop if Tribe=="owens valley indian water commission"
drop if Tribe=="southern plains tribal health board foundation"
drop if Tribe=="central oregon intergovernmental council"
drop if Tribe=="central oregon regional housing authority"
drop if Tribe=="first nations community health source inc"
drop if Tribe=="point no point treaty council"
drop if Tribe=="department of public health-d iv. of ph"
drop if Tribe=="indian board of education for the pierre indian school"
drop if Tribe=="pierre indian learning center"
drop if Tribe=="indian health center of santa clara valley"
drop if Tribe=="dzilth-na-o-dith-hle school board of education, inc."
drop if Tribe=="iac symposium"
drop if Tribe=="skagit river system cooperative"
drop if Tribe=="native american health center, inc."
drop if Tribe=="tohatchi area of opportunity & services, inc."
drop if Tribe=="united indians of all tribes"
drop if Tribe=="north american indian alliance"
drop if Tribe=="north american indian center of boston inc"
drop if Tribe=="santa fe indian school, inc."
drop if Tribe=="santa fe indian school inc"
drop if Tribe=="united indian health services inc"
drop if Tribe=="united south & eastern tribes, inc"
drop if Tribe=="white shield school district"
drop if Tribe=="sonoma county indian health project inc"
drop if Tribe=="shoshone & arapaho tribe inc"
drop if Tribe=="shoshone & arapahoe tribes"
drop if Tribe=="shoshone arapaho head start program"
drop if Tribe=="columbus metropolitan housing authority"
drop if Tribe=="columbus property management & development"
drop if Tribe=="united american indian involvement inc"
drop if Tribe=="western carolina community action, inc."
drop if Tribe=="west ohio community action partnership"
drop if Tribe=="acl wic program"
drop if Tribe=="lawton inter-tribal o & m project"
drop if Tribe=="strong family health center"
drop if Tribe=="tribal solid waste advisory network"
drop if Tribe=="two feathers native american families services"
drop if Tribe=="wabanaki public health & wellness npc"
drop if Tribe=="1854 treaty authority"
drop if Tribe=="1854 authority"
drop if Tribe=="american indian association of tucson, inc."
drop if Tribe=="central tribes of shawnee area"
drop if Tribe=="central valley indian health inc"
drop if Tribe=="all mission indian housing authority"
drop if Tribe=="all tribes american indian charter school"
drop if Tribe=="indian senior center inc"
drop if Tribe=="tribal education departments national assembly co"
drop if Tribe=="united indian health services, inc"
drop if Tribe=="united indian nations inc"
drop if Tribe=="united sioux tribes of south dakota"
drop if Tribe=="upper snake river tribes foundation inc"
drop if Tribe=="fort defiance indian hospital board, inc."
**I'm unsure about this hospital as it is not a tribal org but it serves ony Navajo 
drop if Tribe=="council of 3 rivers american indian center"
drop if Tribe=="southeastern minnesota multi-county housing and redevelopment authority"
drop if Tribe=="the four tribes consortium of oklahoma"
drop if Tribe=="del monte foods, inc."
drop if Tribe=="flagstaff brodertown dormitory bd inc"
drop if Tribe=="flagstaff bordertown dorm brd"
drop if Tribe=="feather river tribal health, inc."
drop if Tribe=="four winds of indian education"
drop if Tribe=="housing authority of billings inc"
drop if Tribe=="housing authority of alameda county"
drop if Tribe=="housing authority of columbus georgia th"
drop if Tribe=="housing authority of champaign county"
drop if Tribe=="housing authority of greene county, alabama"
drop if Tribe=="housing authority of gloucester county"
drop if Tribe=="housing authority of jackson county"
drop if Tribe=="housing authority of joliet"
drop if Tribe=="housing authority of west memphis"
drop if Tribe=="housing authority of yamhill county"
drop if Tribe=="housing authority skagit county"
drop if Tribe=="imperial valley housing authority"
drop if Tribe=="jefferson county housing authority"
drop if Tribe=="jefferson franklin community action corporation"
drop if Tribe=="jefferson parish, housing authority of"
drop if Tribe=="housing authority of boulder county"
drop if Tribe=="housing authority of bowling green"
drop if Tribe=="housing authority of covington"
drop if Tribe=="housing authority of elgin"
drop if Tribe=="housing authority of fort worth"
drop if Tribe=="housing authority of frankfort"
drop if Tribe=="housing authority of salt lake city"
drop if Tribe=="icast (international center for appropriate and sustainable technology)"
drop if Tribe=="hunter health clinic inc"
drop if Tribe=="mact health board inc"
drop if Tribe=="marion county housing authority"
drop if Tribe=="san joaquin county housing authority"
drop if Tribe=="south central mn multicounty hra"
drop if Tribe=="st clair county housing authority"
drop if Tribe=="indian center inc"
drop if Tribe=="indian health board of billings, inc"
drop if Tribe=="indian health care resource center of tulsa inc"
drop if Tribe=="st. clair public housing authority"
drop if Tribe=="united south and eastern tribes inc."
drop if Tribe=="western washington indian employment and training program"
drop if Tribe=="westmoreland county housing authority"
drop if Tribe=="wheeling housing authority"
drop if Tribe=="westland housing commission"
drop if Tribe=="wilmington housing authority"
drop if Tribe=="wisconsin tri-band manpower consortium"
drop if Tribe=="cheyenne-eagle butte airport association inc"
drop if Tribe=="l'refuah medical & rehab center inc"
drop if Tribe=="local affairs, colorado department of"
drop if Tribe=="newport news housing authority"
drop if Tribe=="newnan housing development corporation"
drop if Tribe=="floyd county housing authority"
drop if Tribe=="medford housing authority"
drop if Tribe=="meigs housing authority"
drop if Tribe=="menard county housing authority"
drop if Tribe=="menard county housing authority"
drop if Tribe=="mesilla valley public housing authority"
drop if Tribe=="minneapolis american indian center"
drop if Tribe=="c & m food distributing inc"
drop if Tribe=="abenaki self-help association, inc."
drop if Tribe=="bay county transportation planning organization"
drop if Tribe=="bowery residents' committee, inc."
drop if Tribe=="brattleboro housing authority"
drop if Tribe=="braintree housing authority"
drop if Tribe=="bristol redevelopment and housing authority"
drop if Tribe=="brockton housing authority"
drop if Tribe=="burlington housing authority"
drop if Tribe=="central council tlingit and haida indian tribes of alaska"
drop if Tribe=="chapa-de indian health program, inc."
drop if Tribe=="housing authority of lycoming county"
drop if Tribe=="housing authority of mingo county"
drop if Tribe=="housing authority of myrtle beach"
drop if Tribe=="housing authority of polk county"
drop if Tribe=="housing authority of san luis obispo"
drop if Tribe=="housing authority of utah county"
drop if Tribe=="housing authority of thurston county"
drop if Tribe=="housing authority of vincennes"
drop if Tribe=="housing authority of west memphis"
drop if Tribe=="housing authority st charles"
drop if Tribe=="howard county housing commission"
drop if Tribe=="huntsville housing authority"
drop if Tribe=="idaho housing and finance association"
drop if Tribe=="indian child and family preservation program"
drop if Tribe=="pasco county housing auth"
drop if Tribe=="pasco housing authority"
drop if Tribe=="north central texas council of governments"
drop if Tribe=="north charleston housing authority"
drop if Tribe=="north east community action corporation"
drop if Tribe=="northeast nebraska joint housing agency"
drop if Tribe=="northeast oregon housing authority"
drop if Tribe=="kingsport housing & redevelopment authority"
drop if Tribe=="king county housing authority"
drop if Tribe=="pleasantville housing authority"
drop if Tribe=="rental assistance corp of buffalo"
drop if Tribe=="rockford housing authority"
drop if Tribe=="rockville housing enterprises"
drop if Tribe=="indian family health clinic of great falls, incorporated"
drop if Tribe=="jackson housing authority"
drop if Tribe=="jacksonville housing authority"
drop if Tribe=="portland housing authority"
drop if Tribe=="portsmouth redevelopment & h"
drop if Tribe=="washington county community development agency"
drop if Tribe=="tallahassee housing authority"
drop if Tribe=="vancouver housing authority inc"
drop if Tribe=="virgin islands housing authority"
drop if Tribe=="stewards of affordable housing for the future"
drop if Tribe=="upper midwest american indian center"
drop if Tribe=="kentucky housing corp"
drop if Tribe=="knoxvilles community development corp"
drop if Tribe=="knoxville-knox county planning"
drop if Tribe=="lakewood housing authority"
drop if Tribe=="lakewood tenants organization inc"
drop if Tribe=="lexington housing authority"
drop if Tribe=="lewiston housing authority"
drop if Tribe=="lexington-fayatte urban county housing a"
drop if Tribe=="linn benton housing authority"
drop if Tribe=="loudoun county"
drop if Tribe=="louisville metro housing authority"
drop if Tribe=="lowell housing authority"
drop if Tribe=="macoupin county housing authority"
drop if Tribe=="lynn housing authority"
drop if Tribe=="organization of the forgotten american, inc, the"
drop if Tribe=="parkersburg housing authority"
drop if Tribe=="parma housing agency"
drop if Tribe=="albuquerque united states health service indian hospital"
drop if Tribe=="alexander city housing authority"
drop if Tribe=="alexandria redevelopment & housing authority"
drop if Tribe=="all nations health center inc"
drop if Tribe=="allegheny county housing authority"
drop if Tribe=="boston housing authority"
drop if Tribe=="brookings county housing & redeve"
drop if Tribe=="brownsville housing authority"
drop if Tribe=="lancaster city housing authority"
drop if Tribe=="lansing housing commission"
drop if Tribe=="lawrence county port authority"
drop if Tribe=="lift community action agency inc"
drop if Tribe=="pierce county housing authority"
drop if Tribe=="greenville city housing authority"
drop if Tribe=="mobridge housing authority main office"
drop if Tribe=="palm beach county housing authority"
drop if Tribe=="nd associates of tribal colleges"
drop if Tribe=="new hampshire housing finance authority"
drop if Tribe=="new york city housing authority"
drop if Tribe=="oklahoma city housing authority"
drop if Tribe=="open market esco llc"
drop if Tribe=="red-spectrum communications llc"
drop if Tribe=="prichard housing authority"
drop if Tribe=="randolph county housing authority"
drop if Tribe=="santa fe civic housing authority inc"
drop if Tribe=="sarasota housing authority"
drop if Tribe=="sheffield housing authority"
drop if Tribe=="kankakee county housing authority"
drop if Tribe=="wyatt community development corporation"
drop if Tribe=="acton housing authority"
drop if Tribe=="ada county housing authority"
drop if Tribe=="affiliated tribes of northwest indians financial services"
drop if Tribe=="affiliated tribes of nw indian"
drop if Tribe=="attleboro housing authority"
drop if Tribe=="augusta housing authority"
drop if Tribe=="charleston county housing and redevelopment authority"
drop if Tribe=="chelsea housing authority"
drop if Tribe=="chatham county housing authority"
drop if Tribe=="chattanooga housing authority"
drop if Tribe=="chesapeake redevelopment and housing authority"
drop if Tribe=="chicago housing authority"
drop if Tribe=="chillicothe metro housing authority"
drop if Tribe=="clay county housing & redevelopment auth"
drop if Tribe=="clearwater housing authority"
drop if Tribe=="clovis housing & redevelopment agency inc"
drop if Tribe=="dakota county community development agency"
drop if Tribe=="dallas county texas"
drop if Tribe=="denver indian health & family services inc"
drop if Tribe=="derby housing authority"
drop if Tribe=="detroit housing commission"
drop if Tribe=="domestic awardees (undisclosed)"
drop if Tribe=="east tennessee human resource agency, inc."
drop if Tribe=="east orange housing authority"
drop if Tribe=="east providence housing authority inc"
drop if Tribe=="eight north pueblo, nm"
drop if Tribe=="eight northern indian pueblos"
drop if Tribe=="eight northern indian pueblos council, inc. p"
drop if Tribe=="framingham housing authority"
drop if Tribe=="employment and training administration"
drop if Tribe=="enterprise community partners, inc."
drop if Tribe=="circle of nations"
drop if Tribe=="constortium against substance abuse"
drop if Tribe=="alamo community college district"
drop if Tribe=="black hills center for american indian health"
drop if Tribe=="bemidji area indian health service"
drop if Tribe=="benoit school district"
drop if Tribe=="college of the menominee"
drop if Tribe=="fife public schools"
drop if Tribe=="fife school district"
drop if Tribe=="cdw government llc"
drop if Tribe=="foothills academy inc"
drop if Tribe=="bonsall unified school district"
drop if Tribe=="bonsall union school district"
drop if Tribe=="binger-oney public school"
drop if Tribe=="housing and community development, massachusetts department of"
drop if Tribe=="housing & redevelopment authority of duluth"
drop if Tribe=="housing auth of savannah"
drop if Tribe=="housing auth of st marys co"
drop if Tribe=="housing authorities-st louis"
drop if Tribe=="housing authority & community service agency of lane county"
drop if Tribe=="housing authority of glasgow"
drop if Tribe=="housing authority armstrong"
drop if Tribe=="housing authority of birmingham district"
drop if Tribe=="housing authority of greenville inc"
drop if Tribe=="housing authority of racine coun"
drop if Tribe=="indianapolis housing agency"
drop if Tribe=="housing & redevelopment authority of vir"
drop if Tribe=="housing authority of anderson"
drop if Tribe=="housing authority of biloxi"
drop if Tribe=="island county housing authority of"
drop if Tribe=="housing authority of henry county"
drop if Tribe=="housing authority of indiana county"
drop if Tribe=="housing authority of prince george's county"
drop if Tribe=="housing authority of st louis park"
drop if Tribe=="housing authority of springfield"
drop if Tribe=="indiana resource center f"
drop if Tribe=="housing commission of anne arundel county"
drop if Tribe=="housing finance agency oklahoma"
drop if Tribe=="housing authority of kc mo"
drop if Tribe=="housing authority of kings county"
drop if Tribe=="housing authority of lakeland"
drop if Tribe=="housing authority of northd c"
drop if Tribe=="housing authority of kokomo"
drop if Tribe=="housing authority of maricopa"
drop if Tribe=="hustler  village of"
drop if Tribe=="inlivian"
drop if Tribe=="inetnon amot natibu ammwelil safeyal faluwasch"
drop if Tribe=="inca community services inc"
drop if Tribe=="hunkpapa development llc"
drop if Tribe=="hud-kiowa tdhe"
drop if Tribe=="ilisagvik college" //Alaska's tribal college
drop if Tribe=="heat watch llc"
drop if Tribe=="hoonah indian association"
drop if Tribe=="wiconi wawokiya, inc"
drop if Tribe=="wiconi wawokiya, inc."
drop if Tribe=="wiconi wawokiya inc"
drop if Tribe=="walters public schools"
drop if Tribe=="walters school district i-001"
drop if Tribe=="wayne county school district"
drop if Tribe=="wallowa school district 12"
drop if Tribe=="walkerville public schools"
drop if Tribe=="wakanyeja pawicayapi"
drop if Tribe=="nebraska indian community college"
drop if Tribe=="alu like inc"

drop if strpos(Tribe, "inter-tribal")==1 
drop if strpos(Tribe, "inter tribal")==1 
drop if strpos(Tribe, "intra-tribal")==1 
drop if strpos(Tribe, "bia")==1 
drop if strpos(Tribe, "indian affairs bureau of")==1 
drop if strpos(Tribe, "indian affairs, bureau of")==1
drop if strpos(Tribe, "bureau of indian affairs")==1 
drop if strpos(Tribe, "indian health service")==1 
drop if strpos(Tribe, "city of")==1
drop if strpos(Tribe, "county of")==1
drop if strpos(Tribe, "multiple recipients")==1
drop if strpos(Tribe, "housing authority of the city of")==1
drop if strpos(Tribe, "housing authority of city")==1
drop if strpos(Tribe, "housing authority of county of")==1
drop if strpos(Tribe, "housing authority of the county of ")==1
drop if strpos(Tribe, "housing authority of the town of ")==1
drop if strpos(Tribe, "housing authority of town of ")==1
drop if strpos(Tribe, "housing authority of the township of ")==1
drop if strpos(Tribe, "national")==1
drop if strpos(Tribe, "village of")==1
drop if strpos(Tribe, "town of")==1
drop if strpos(Tribe, "san diego")==1
drop if strpos(Tribe, "arizona")==1
drop if strpos(Tribe, "arkansas")==1
drop if strpos(Tribe, "sacramento")==1
drop if strpos(Tribe, "intertribal")==1
drop if strpos(Tribe, "mississippi regional housing")==1
drop if strpos(Tribe, "southern ca")==1
drop if strpos(Tribe, "municipal")==1
drop if strpos(Tribe, "metropolitan")==1
drop if strpos(Tribe, "northern pueblos")==1
drop if strpos(Tribe, "orange county")==1
drop if strpos(Tribe, "scott county")==1
drop if strpos(Tribe, "springfield")==1
drop if strpos(Tribe, "american indian")==1
drop if strpos(Tribe, "regional")==1
drop if strpos(Tribe, "tennessee")==1
drop if strpos(Tribe, "seattle")==1
drop if strpos(Tribe, "lehigh county")==1
drop if strpos(Tribe, "lee county")==1
drop if strpos(Tribe, "lake county")==1
drop if strpos(Tribe, "brown county")==1
drop if strpos(Tribe, "broward county")==1
drop if strpos(Tribe, "puerto rico")==1
drop if strpos(Tribe, "public housing")==1
drop if strpos(Tribe, "mid sioux opportunity inc")==1 

**for some reason, stropos function doesn't get all substrings so I'm using another one: 
drop if regexm(Tribe, "county of")==1 & tribe_id==.
drop if regexm(Tribe, "city of")==1 & tribe_id==.
drop if regexm(Tribe, "town of")==1 & tribe_id==.
drop if regexm(Tribe, "metropolitan")==1 & tribe_id==.
drop if regexm(Tribe, "regional")==1 & tribe_id==.
drop if regexm(Tribe, "native american")==1 & tribe_id==.
drop if regexm(Tribe, "municipio de")==1 & tribe_id==.
drop if regexm(Tribe, "united indian")==1 & tribe_id==.
drop if regexm(Tribe, "state university")==1 & tribe_id==.
drop if regexm(Tribe, "fresno")==1 & tribe_id==.
drop if regexm(Tribe, "hawaii")==1 & tribe_id==.
drop if regexm(Tribe, "municipality of")==1 & tribe_id==.
drop if regexm(Tribe, "state of")==1 & tribe_id==.
drop if regexm(Tribe, "franklin")==1 & tribe_id==.
drop if regexm(Tribe, "guam")==1 & tribe_id==.
drop if regexm(Tribe, "adams ")==1 & tribe_id==.
drop if regexm(Tribe, "fulton county")==1 & tribe_id==.
drop if regexm(Tribe, "adams ")==1 & tribe_id==.
drop if regexm(Tribe, "cook county")==1 & tribe_id==.
drop if regexm(Tribe, "contra costa county")==1 & tribe_id==.
drop if regexm(Tribe, "madison")==1 & tribe_id==.
drop if regexm(Tribe, "municipal")==1 & tribe_id==.
drop if regexm(Tribe, "holyoke")==1 & tribe_id==.
drop if regexm(Tribe, "pinellas county")==1 & tribe_id==.
drop if regexm(Tribe, "imperial")==1 & tribe_id==.
drop if regexm(Tribe, "andes")==1 & tribe_id==.
drop if regexm(Tribe, "baltimore")==1 & tribe_id==.
drop if regexm(Tribe, "bank")==1 & tribe_id==.
drop if regexm(Tribe, "beaufort")==1 & tribe_id==.
drop if regexm(Tribe, "belmont")==1 & tribe_id==.
drop if regexm(Tribe, "benwood")==1 & tribe_id==.
drop if regexm(Tribe, "bernalillo")==1 & tribe_id==.
drop if regexm(Tribe, "columbus")==1 & tribe_id==.
drop if regexm(Tribe, "columbia")==1 & tribe_id==.
drop if regexm(Tribe, "cumberland")==1 & tribe_id==.
drop if regexm(Tribe, "church")==1 & tribe_id==.
drop if regexm(Tribe, "friends")==1 & tribe_id==.
drop if regexm(Tribe, "milton housing")==1 & tribe_id==.

gen dummy=1 if regexm(Tribe, "university of")==1 & tribe_id==.
br Tribe if dummy==1
drop if dummy==1
drop dummy

**state-recognized & unrecognized tribes:
**note that some Alaska tribes were dropped above
drop if Tribe=="haliwa-saponi indian tribe" | Tribe=="haliwa-saponi indian tribe inc." | Tribe=="haliwa-saponi tribe inc" | Tribe=="eastern pequot nation wut" | Tribe=="mowa band of choctaw indians" | Tribe=="mowa choctaw housing authority" | Tribe=="united cherokee aniyunwiya nation" | Tribe=="united houma nation inc" | Tribe=="united cherokee ani-yun-wiya nation" | Tribe=="lumbee land development inc" | Tribe=="lumbee nation tribal programs, inc." | Tribe=="lumbee regional development associates inc" | Tribe=="lumbee tribe of tribal council, the" | Tribe=="ma chis lower creek tribe of alabama" | Tribe=="ma-chis lower creek indian tribe enterprises, inc." | Tribe=="machias historical society" | Tribe=="machis lower creek indian tribe of alabama" | Tribe=="pee dee indian tribe sc" | Tribe=="lower muskogee creek tribe east of the mississippi inc, the" | Tribe=="waccamaw siouan indian tribe, inc." | Tribe=="nipmuc nation tribal council, inc., the" | Tribe=="haliwa saponi tribal school" | Tribe=="haliwa - saponi tribe, inc." | Tribe=="haliwa indian tribe, inc" | Tribe=="choctaw-apache community of ebarb, inc." | Tribe=="euchee tribe of indians" | Tribe=="juaneno band of mission indians" | Tribe=="wyandot of anderdon nation, the" | Tribe=="nanticoke lenni-lenape indians of nj, inc" | Tribe=="wa hoh tribal business community" | Tribe=="accohannock indian tribe, inc." | Tribe=="meherrin indian tribe" | Tribe=="eel river tribe of indiana, inc" | Tribe=="coharie intra tribal council inc." | Tribe=="coharie intra-tribal council, inc." | Tribe=="coharie people inc" | Tribe=="fernandeno tataviam band of mission indians" | Tribe=="brothertown nation, inc" | Tribe=="high plains indians, inc" | Tribe=="tubatulabals of kern valley" | Tribe=="pointe au chien indian tribe" | Tribe=="occaneechi band of the saponi nation" | Tribe=="nor-el-muk band of wintu indians of northern california"

**the following tribe is federally recognized but not serviced:
drop if Tribe=="the chickamauga nation" 

drop if regexm(Tribe, "burt lake band")==1 & tribe_id==.
**burt lake band of ottawa & chippewa indians got federal recognition around 2022-2023, but they are not in our roaster of federally recognized tribes 

**Apache tribes check, since there are multiple apache tribes
tab recipient_state_code Tribe if tribe_id==7 //OK
tab recipient_state_code Tribe if tribe_id==174 //NM
tab recipient_state_code Tribe if tribe_id==97 //AZ
tab recipient_state_code Tribe if tribe_id==99 //OK
tab recipient_state_code Tribe if tribe_id==277 //AZ
tab recipient_state_code Tribe if tribe_id==362 //AZ
tab recipient_state_code Tribe if tribe_id==373 //AZ

tab recipient_state_code if Tribe=="housing authority of apache tribe" //OK
replace tribe_id=99 if Tribe=="housing authority of apache tribe"

**Shoshone tribes check
tab recipient_state_code Tribe if tribe_id==82 //WY
tab recipient_state_code Tribe if tribe_id==96 //NV
tab recipient_state_code Tribe if tribe_id==199 //UT
tab recipient_state_code Tribe if tribe_id==210 //NV
tab recipient_state_code Tribe if tribe_id==298 //ID
tab recipient_state_code Tribe if tribe_id==299 //NV
tab recipient_state_code Tribe if tribe_id==323 //NV
tab recipient_state_code Tribe if tribe_id==332 //CA

tab recipient_state_code if Tribe=="the shoshone tribe" //WY
replace tribe_id=82 if Tribe=="the shoshone tribe"
tab recipient_state_code if Tribe=="shoshone tribe" //WY
replace tribe_id=82 if Tribe=="shoshone tribe"

**Chippewa tribes check
tab Tribe recipient_state_code if tribe_id==49 //MT
tab Tribe recipient_state_code if tribe_id==180 //MN
tab Tribe recipient_state_code if tribe_id==305 //WI
tab Tribe recipient_state_code if tribe_id==311 //WI
tab Tribe recipient_state_code if tribe_id==102 //MI
tab Tribe recipient_state_code if tribe_id==148 //WI

tab recipient_state_code Tribe if Tribe=="chippewa housing authority" //WI
tab primary_place_of_performance_cit if Tribe=="chippewa housing authority"
replace tribe_id=148 if Tribe=="chippewa housing authority"

*******************************************************************

**should we drop these? : 
**drop if tribe_id!=. & business_types_description=="INDIAN/NATIVE AMERICAN TRIBAL GOVERNMENT (OTHER THAN FEDERALLY-RECOGNIZED)"

**count the number of awards per recipient
bysort Tribe: gen sum =_N

**combine award amounts by recipient and check the total amount if tribe_id==.
bysort Tribe: egen tot_amount = total(total_obligated_amount) if tribe_id==.
br if tot_amount>1000000 & tribe_id==.
br Tribe if tot_amount<=1000000 & tot_amount>=500000 & tribe_id==.  

count if tribe_id==.
**4,195

drop if tribe_id==.
describe, short



