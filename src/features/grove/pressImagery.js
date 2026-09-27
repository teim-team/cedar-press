/**
 * REVIEW OWNER: Havala
 *
 * The photographs the door's use cases carry, and how to ask for one.
 *
 * WHERE THEY COME FROM
 * Lumecon's sector image system (`lumecon-website`, `scripts/naics/`). The
 * files under `public/press/sectors/` are that system's processed duotone
 * derivatives, copied in, never imported at build time and never the
 * originals. Every file, its Shutterstock asset and license IDs and its row
 * in Lumecon's license manifest are listed in `docs/IMAGE_LICENSES.md`.
 *
 * THE WASH BELONGS TO THE SECTOR, NOT TO THE AUDIENCE
 * In Lumecon's system a sector's wash is part of its identity: bronze means
 * Wholesale or Real Estate, gold means Professional Services, and slate
 * means "no sector". So an image keeps its own sector's wash wherever it
 * appears here; recolouring one to suit an audience would assert an
 * industry the photograph does not show. `wash` below is recorded for the
 * tests and the license note, and is never applied: the colour is in the
 * file.
 *
 * WHAT MAY BE CHOSEN
 * Only photographs with no identifiable person. The Shutterstock Standard
 * license forbids implying that the people depicted endorse Lumecon, and a
 * face beside a sentence about what an audience accomplishes reads as that
 * audience's endorsement. Lumecon's healthcare, professional, management,
 * education and information photographs all show faces and are not used.
 * The `-v2` photographs Lumecon's manifest does not yet list (every sector
 * but four) are also left out, so every file here has a manifest row. Only
 * photographs some use case's pool uses are copied in.
 *
 * SIZES
 * Each image ships three cuts: a 3:2 page size, a 3:2 grid size (`-sm`) and
 * a 5:2 banner (`-wide`). The two context textures come from 1000px masters,
 * so theirs are smaller (Lumecon's LICENSES.md, "the masters are 1000px").
 * The tests read each file's real dimensions and compare them with these.
 */

/** Where the copied files are served from. */
export const SECTOR_IMAGE_DIR = "/press/sectors";

const SECTOR_SIZES = Object.freeze({ main: [1200, 800], sm: [600, 400], wide: [1500, 600] });
const CONTEXT_SIZES = Object.freeze({ main: [840, 560], sm: [600, 400], wide: [1000, 400] });

const image = (sector, wash, sizes = SECTOR_SIZES) => Object.freeze({ sector, wash, sizes });

/**
 * Every photograph the door may show, by Lumecon slug. `sector` is Lumecon's
 * name for the category it belongs to, never a claim this page makes.
 */
export const SECTOR_IMAGES = Object.freeze({
  utilities: image("Utilities", "gold"),
  "utilities-v2": image("Utilities", "gold"),
  hospitality: image("Accommodation and Food Services", "bronze"),
  construction: image("Construction", "teal"),
  manufacturing: image("Manufacturing", "teal"),
  "manufacturing-v2": image("Manufacturing", "teal"),
  transportation: image("Transportation and Warehousing", "teal"),
  wholesale: image("Wholesale Trade", "bronze"),
  agriculture: image("Agriculture, Forestry, Fishing and Hunting", "green"),
  retail: image("Retail Trade", "gold"),
  finance: image("Finance and Insurance", "green"),
  otherservices: image("Other Services", "gold"),
  realestate: image("Real Estate and Rental and Leasing", "bronze"),
  // Not sectors: textures for a subject with no defensible sector, washed in
  // slate so the colour does not assert an industry.
  "context-cedar": image(null, "slate", CONTEXT_SIZES),
  "context-lattice": image(null, "slate", CONTEXT_SIZES),
});

/** The file for one cut of one image. */
export function imageFile(slug, cut = "main") {
  const suffix = cut === "main" ? "" : `-${cut}`;
  return `${SECTOR_IMAGE_DIR}/${slug}${suffix}.webp`;
}

/**
 * Everything a `<picture>` needs for one image, or null for an unknown slug:
 * the 3:2 pair for a side panel and the 5:2 banner for a phone.
 */
export function imageSources(slug) {
  const entry = SECTOR_IMAGES[slug];
  if (!entry) return null;
  const { main, sm, wide } = entry.sizes;
  return Object.freeze({
    slug,
    src: imageFile(slug, "sm"),
    srcSet: `${imageFile(slug, "sm")} ${sm[0]}w, ${imageFile(slug, "main")} ${main[0]}w`,
    width: sm[0],
    height: sm[1],
    wideSrcSet: `${imageFile(slug, "wide")} ${wide[0]}w`,
    wideWidth: wide[0],
    wideHeight: wide[1],
  });
}
