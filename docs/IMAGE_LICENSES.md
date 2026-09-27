# Image licenses

The photographs on the door's use cases are Lumecon's, processed through
Lumecon's sector image system and copied into this repository. This file is
the record of which files were copied, the license each one carries, and
which use case may show them. It is checked by
`src/features/grove/pressJobs.test.js`, which fails if a copied file or a use
case's image pool is missing from it.

## Where they come from

- **Source.** `lumecon-website`, `public/naics/`, at commit `e38ac5b`
  (2026-09-20). Each file here is byte-for-byte that repository's file, so the
  SHA-256 prefixes below match both.
- **Processed derivatives only.** These are the duotone `.webp` files that
  `lumecon-website/scripts/naics/duotone.mjs` (and `fallbacks.mjs` for the
  two context textures) cut from the licensed photographs. No original
  photograph is in this repository, and none is served.
- **Copied, not imported.** Nothing here reads `lumecon-website` at build time.
  To refresh a file, copy the processed derivative again and update its row.
- **The license record is Lumecon's.** `lumecon-website/scripts/naics/LICENSES.md`
  is the manifest: every photograph that enters the pipeline gets a row there
  before its processed files are committed. The "Manifest row" column names
  the row each file here rests on. Every file copied has one; Lumecon's other
  `-v2` photographs (every sector but four) have Shutterstock IDs in their
  source filenames but no manifest row yet, so none of them is used.

## The license, in plain terms

All sector photographs are licensed to Lumecon Inc. under the Shutterstock
**Standard license** (confirmed against the account's License history on
2026-07-26 for the original cohort; the two `-v2` photographs here are
listed separately in the manifest with their asset and license IDs). The two
context textures are covered by Lumecon's active Shutterstock subscription;
their IDs are `<PENDING>` in Lumecon's own manifest, which records why.

What the Standard license permits here: use in the product's interface. What
it does not: resale of the image, redistribution of the original, or **use in
a way that suggests the people depicted endorse Lumecon**. That last rule
decided the selection:

- **No identifiable person.** A face beside a sentence about what an audience
  accomplishes reads as that audience's endorsement. Lumecon's healthcare,
  professional-services, management, education and information photographs
  all show faces, and none is used. Where people appear in the files below
  (construction, manufacturing, retail, finance, other services), they are
  seen from above, from behind, below the face, or as hands.
- **Illustrative.** The door says once that its photography is illustrative
  and does not identify Cedar Press customers.
- **Dignity, and no council chamber.** Neither of Lumecon's Tribal
  Government photographs is used. The lead one is feather regalia with
  beadwork, and a ceremonial object is not decoration for a benchmarking
  card; the second is a hall of flags, and the owner asked that "Tribal
  Nations = council chamber" not become the shorthand. The Tribal Nations
  pool is economy sectors instead. (The door's navy passage already carries
  the hall of flags, from `public/photo/`, under its own record.)

## The wash belongs to the sector

In Lumecon's system a sector's wash is part of its identity (bronze means
Wholesale or Real Estate, gold means Professional Services, slate means "no
sector"). Each file keeps its own sector's wash; no photograph is recoloured
to suit an audience.

## Files

Sizes: `<slug>.webp` 1200x800, `-sm` 600x400, `-wide` 1500x600; the two context
textures come from 1000px masters and are 840x560, 600x400 and 1000x400.

| Slug | Wash | Shutterstock asset ID | License ID | Subject | Manifest row | Files (size, SHA-256 prefix) |
| --- | --- | --- | --- | --- | --- | --- |
| `utilities` | gold | 2750775877 | 806729298773 | Transmission towers at dusk | Gold wash: `utilities` | `utilities.webp` (138 KB, `9d4e24ba81178638`), `utilities-sm.webp` (31 KB, `f515aab751e9fa1c`), `utilities-wide.webp` (121 KB, `7741d2fdb2b41866`) |
| `utilities-v2` | gold | 2760326511 | 806816496991 | Public-page v2 image (wind turbines over farmland) | Gold wash: `utilities-v2` | `utilities-v2.webp` (41 KB, `733524ee6aee3a1b`), `utilities-v2-sm.webp` (17 KB, `69ccb482deae66a6`), `utilities-v2-wide.webp` (33 KB, `4948470eb045f9d8`) |
| `hospitality` | bronze | 2791267727 | 806731004894 | Hotel guest room | Bronze wash: `hospitality` | `hospitality.webp` (44 KB, `2940ff2b51b8a0c3`), `hospitality-sm.webp` (12 KB, `359180e62b585873`), `hospitality-wide.webp` (32 KB, `7fe3a204f5afc82b`) |
| `construction` | teal | 2650575753 | 806729367383 | Rebar crew on a structural deck (aerial; no face is legible) | Teal wash: `construction` | `construction.webp` (220 KB, `f88e4158a8613a62`), `construction-sm.webp` (65 KB, `4976033e47801793`), `construction-wide.webp` (151 KB, `cb89972f3454e414`) |
| `manufacturing` | teal | 2761678059 | 806729672016 | Plant floor with crew (seen from behind) | Teal wash: `manufacturing` | `manufacturing.webp` (89 KB, `a612ad8dbf74138a`), `manufacturing-sm.webp` (28 KB, `119269e5bb93e1de`), `manufacturing-wide.webp` (56 KB, `c378f1ff5732fcb4`) |
| `manufacturing-v2` | teal | 2773176257 | 806816679034 | Public-page v2 image (vehicle chassis on an assembly line) | Teal wash: `manufacturing-v2` | `manufacturing-v2.webp` (78 KB, `a685ae48763999d5`), `manufacturing-v2-sm.webp` (33 KB, `372f7e9efb32d878`), `manufacturing-v2-wide.webp` (59 KB, `640ad08ab2310861`) |
| `transportation` | teal | 2755727965 | 806729746252 | Cargo ships at sea | Teal wash: `transportation` | `transportation.webp` (71 KB, `3d2fe1b2b3552086`), `transportation-sm.webp` (16 KB, `c35124602d0461b8`), `transportation-wide.webp` (67 KB, `e5cb769379f58ada`) |
| `wholesale` | bronze | 2756043513 | 806730308942 | Distribution docks, aerial | Bronze wash: `wholesale` | `wholesale.webp` (78 KB, `acec5698fc052711`), `wholesale-sm.webp` (24 KB, `c715bd1dd9d0819f`), `wholesale-wide.webp` (59 KB, `0d5c56bb074ba4ba`) |
| `agriculture` | green | 2742674003 | 806728869271 | Center-pivot irrigation | Green wash: `agriculture` | `agriculture.webp` (75 KB, `634bc8cf347b574e`), `agriculture-sm.webp` (25 KB, `b979ce6d5c2f4270`), `agriculture-wide.webp` (70 KB, `3a8ad87f5d02c8fc`) |
| `retail` | gold | 2769581455 | 806730275771 | Grocery shopper with a basket (no face in frame) | Gold wash: `retail` | `retail.webp` (69 KB, `460af9c81ababd3c`), `retail-sm.webp` (23 KB, `2e3b3500b78d5519`), `retail-wide.webp` (64 KB, `66690f8feafc53d8`) |
| `finance` | green | 2757439509 | 806730469490 | Teller counting out cash (hands only) | Green wash: `finance` | `finance.webp` (24 KB, `d3d9edd067585de0`), `finance-sm.webp` (9 KB, `d2f46399499be98c`), `finance-wide.webp` (18 KB, `14a07a879dc4ce74`) |
| `otherservices` | gold | 2699860863 | 806731060268 | Joined hands, community organization (hands only) | Gold wash: `otherservices` | `otherservices.webp` (30 KB, `d7c73079375b27a9`), `otherservices-sm.webp` (12 KB, `6c6d48f7cd036055`), `otherservices-wide.webp` (28 KB, `76760f8cb2fa3315`) |
| `realestate` | bronze | 2753397735 | 806730589724 | Mid-rise apartment blocks | Bronze wash: `realestate` | `realestate.webp` (162 KB, `d892d80183efbe59`), `realestate-sm.webp` (37 KB, `2ca623522454aa2f`), `realestate-wide.webp` (155 KB, `949830ec11fe7de8`) |
| `context-cedar` | slate | `<PENDING>` | `<PENDING>` | Cut face of cedar, growth rings | Contextual fallback covers: `context-cedar` | `context-cedar.webp` (116 KB, `7f1eab6464470beb`), `context-cedar-sm.webp` (65 KB, `50d261848048b45a`), `context-cedar-wide.webp` (103 KB, `ae364a4f396f0e7b`) |
| `context-lattice` | slate | `<PENDING>` | `<PENDING>` | Light falling through a screen | Contextual fallback covers: `context-lattice` | `context-lattice.webp` (18 KB, `b482025c0f2782c5`), `context-lattice-sm.webp` (11 KB, `f4138769bfda616c`), `context-lattice-wide.webp` (14 KB, `fd4c32f71592593c`) |

## Image pools by use case

Each use case rotates through its pool, one photograph per visit
(`AUDIENCE_JOBS[].imagePool` in `src/features/grove/pressJobs.js`).

| Use case | Job | Pool, in order | Why |
| --- | --- | --- | --- |
| Tribal Nations | Economic development | `construction`, `utilities-v2`, `manufacturing-v2`, `hospitality` | Owner: economy sectors (hospitality, energy, construction, manufacturing, healthcare), not a council chamber. An exterior leads; the hotel room is an interior and comes last. Healthcare shows faces, so it is left out. |
| ANCs and NHOs | Competitive intelligence | `transportation`, `manufacturing`, `construction` | Logistics, industry and construction: the federal-business and operating side of an ANC or NHO portfolio. |
| Native enterprises | Partner discovery | `manufacturing-v2`, `agriculture`, `retail`, `wholesale` | Rotating sectors, as the owner asked: manufacturing, agriculture, retail, wholesale. |
| Banks, lenders and investors | Due diligence | `finance`, `realestate` | Finance, then property: diligence before financing. Hands only; no face. |
| Native nonprofits | Competitive funding | `otherservices`, `context-cedar` | Community organization (hands only), then the cedar texture where no sector fits. |
| Foundations and philanthropy | Investment opportunity | `otherservices`, `realestate` | Owner: health, housing, education, community services. Health and education show faces; community services and housing remain. |
| Businesses working in Indian Country | Market entry | `construction`, `wholesale`, `transportation`, `finance` | Owner: construction, logistics, professional services, tech, finance. Professional services and tech show faces, so logistics is carried twice. |
| Universities and researchers | Research | `context-lattice`, `context-cedar` | Research is not a sector, and the education photograph shows faces: the two slate context textures. |
| Journalists and newsrooms | Journalism | `context-cedar`, `context-lattice` | No sector: the two slate context textures, in the other order. |
| Advisors and professional services | Due diligence | `context-lattice`, `context-cedar` | Professional services and management show faces, and a handshake beside this sentence reads as endorsement: slate textures. |
| Economic development, investors and outside partners | Economic development | `utilities`, `agriculture`, `construction` | Infrastructure, agriculture and construction: where outside capital and partnership typically land. |
