// Public article cards only. Subscriber bodies live in server/cedar_press/articles.json.
import { pressArticlePath } from "./pressRoutes.js";

export const BLOCK = Object.freeze({ P: "p", H2: "h2", PULL: "pull", FIGURE: "figure", IMAGE: "image", PAIR: "pair" });
export const TBN_URL = "https://tribalbusinessnews.com";
export const TBN_PLANS_URL = `${TBN_URL}/subscribe`;
export const LUMECON_URL = "https://lumecon.ai";
export const LUMECON_TEAM_URL = `${LUMECON_URL}/team/`;
export const ARTICLE_IMAGE = Object.freeze({ width: 1500, height: 600 });

export const PRESS_ARTICLES = Object.freeze([
  {
    "id": "brief-owned",
    "hosted": true,
    "demonstration": false,
    "tone": "gold",
    "image": "/pitch/lanes/construction-wide.webp",
    "imageAlt": "Crews working a large construction site",
    "caption": "White Earth Nation's certified list runs heavily to the building trades: construction, drywall, tile and site services, most of it first-preference certified.",
    "datasetId": "owned",
    "draws": [
      "owned"
    ],
    "tag": "Original Research",
    "title": "The first nation-shared roster of individually owned Native businesses is in",
    "dek": "White Earth Nation's TERO sent its certified Indian-owned business list in answer to a request through the office's public contact, the first roster in a dataset of the businesses no federal register counts.",
    "date": "August 2026",
    "byline": "Elijah S. Moreno",
    "minutes": 3
  }
].map(Object.freeze));

export function articlesDrawingOn(collectionId, articles = PRESS_ARTICLES) {
  if (!collectionId) return [];
  return articles.filter((article) =>
    (article.draws ?? (article.datasetId ? [article.datasetId] : [])).includes(collectionId),
  );
}

export function articleHref(article) {
  return article.hosted ? pressArticlePath(article.id) : article.href;
}
