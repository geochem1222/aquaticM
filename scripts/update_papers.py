#!/usr/bin/env python3
"""Update paper metadata for the aquatic metabolism static tracker."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"

def semantic_api_key_from_env() -> str | None:
    for name in [
        "SEMANTIC_SCHOLAR_API_KEY",
        "S2_API_KEY",
        "SEMANTIC_API_KEY",
        "SEMANTIC_SCHOLAR_API",
        "S2_API",
    ]:
        value = os.environ.get(name)
        if value:
            return value
    return None


WATER_TERMS = [
    "river",
    "stream",
    "creek",
    "lake",
    "reservoir",
    "pond",
    "ditch",
    "canal",
    "tidal creek",
    "wetland",
    "marsh",
    "mangrove",
    "estuary",
    "sediment",
    "hyporheic zone",
]

METABOLISM_TERMS = [
    "ecosystem metabolism",
    "stream metabolism",
    "lake metabolism",
    "aquatic metabolism",
    "gross primary production",
    "ecosystem respiration",
    "net ecosystem production",
    "dissolved oxygen",
    "oxygen dynamics",
    "carbon cycling",
    "methane emission",
    "carbon dioxide flux",
    "greenhouse gas",
    "nutrient cycling",
    "nitrogen cycling",
    "phosphorus cycling",
    "microbial metabolism",
    "methanotrophy",
    "hypoxia",
]

SEED_QUERIES = [
    '"ecosystem metabolism" freshwater',
    '"aquatic ecosystem metabolism"',
    '"stream metabolism" "dissolved oxygen"',
    '"lake metabolism" "dissolved oxygen"',
    '"gross primary production" "ecosystem respiration" freshwater',
    '"net ecosystem production" aquatic',
    '"dissolved oxygen" "ecosystem respiration" stream',
    '"methane emission" pond freshwater',
    '"carbon dioxide flux" river lake',
    '"nutrient cycling" freshwater metabolism',
]

SEARCH_QUERIES = SEED_QUERIES + [
    f'"{water}" "{process}"'
    for water in WATER_TERMS
    for process in METABOLISM_TERMS
]

TAG_RULES = {
    "river": [" river", " rivers", " stream", " streams", " creek", " creeks", " hyporheic"],
    "lake": [" lake", " lakes", " reservoir", " reservoirs"],
    "pond": [" pond", " ponds", " small water bod"],
    "ditch": [" ditch", " ditches", " canal", " canals", " tidal creek", " tidal creeks"],
    "wetland": [" wetland", " wetlands", " marsh", " mangrove", " saltmarsh", " estuary"],
    "sediment": [" sediment", " sediments", " benthic", " hyporheic"],
    "oxygen": [" dissolved oxygen", " oxygen", " reaeration", " reaeration", " hypoxia", " anoxia"],
    "metabolism": [
        " ecosystem metabolism",
        " metabolism",
        " gross primary production",
        " primary production",
        " ecosystem respiration",
        " respiration",
        " net ecosystem production",
        " gpp",
        " er ",
        " nep",
    ],
    "carbon": [" carbon", " methane", " ch4", " co2", " carbon dioxide", " organic matter", " doc"],
    "nutrient": [" nitrogen", " phosphorus", " nutrient", " nitrate", " ammonium", " phosphate", " eutrophication"],
    "microbe": [" microbial", " bacteria", " bacterial", " methanotroph", " methanotrophy", " virus", " grazer"],
    "greenhouse": [" methane", " ch4", " carbon dioxide", " co2", " greenhouse gas"],
}

NOISE_TERMS = [
    "patient",
    "clinical",
    "vaccine",
    "cancer",
    "tumor",
    "mouse",
    "mice",
]


def request_json(url: str, params: dict[str, str | int], email: str | None = None, api_key: str | None = None) -> dict[str, Any]:
    headers = {"User-Agent": build_user_agent(email)}
    if api_key:
        headers["x-api-key"] = api_key
    request = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}", headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=50) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt < 2:
                time.sleep(int(error.headers.get("Retry-After", "8")) + attempt * 4)
                continue
            raise
        except urllib.error.URLError:
            if attempt < 2:
                time.sleep(3 + attempt * 4)
                continue
            raise


def build_user_agent(email: str | None) -> str:
    contact = f" mailto:{email}" if email else ""
    return f"aquatic-metabolism-tracker/1.0{contact}"


def fetch_semantic_scholar(retmax: int, email: str | None, api_key: str | None, query_limit: int | None = None) -> list[dict[str, Any]]:
    queries = SEARCH_QUERIES[:query_limit] if query_limit else SEARCH_QUERIES
    per_query = max(15, min(80, retmax // max(1, len(queries)) + 12))
    fields = ",".join([
        "paperId",
        "title",
        "abstract",
        "year",
        "publicationDate",
        "venue",
        "journal",
        "authors",
        "externalIds",
        "url",
        "citationCount",
        "influentialCitationCount",
        "referenceCount",
        "openAccessPdf",
    ])
    papers: list[dict[str, Any]] = []
    for query in queries:
        params: dict[str, str | int] = {"query": query, "limit": per_query, "fields": fields}
        try:
            data = request_json(SEMANTIC_SCHOLAR_BASE, params, email, api_key)
        except urllib.error.HTTPError as error:
            if error.code == 429:
                break
            raise
        query_tags = classify(query)
        papers.extend(enrich_query_tags(parse_semantic_paper(item), query_tags) for item in data.get("data", []))
        time.sleep(0.35 if api_key else 1.05)
    return [paper for paper in papers if paper and is_relevant(paper)]


def parse_semantic_paper(item: dict[str, Any]) -> dict[str, Any]:
    external_ids = item.get("externalIds") or {}
    journal = item.get("venue") or (item.get("journal") or {}).get("name", "")
    doi = normalize_doi(external_ids.get("DOI", ""))
    publication_date = item.get("publicationDate") or (f"{item.get('year')}-01-01" if item.get("year") else "")
    open_pdf = item.get("openAccessPdf") or {}
    title = item.get("title") or ""
    abstract = item.get("abstract") or ""
    return {
        "id": item.get("paperId", ""),
        "source": "Semantic Scholar",
        "pmid": external_ids.get("PubMed", ""),
        "doi": doi,
        "title": title,
        "authors": [author.get("name", "") for author in item.get("authors", []) if author.get("name")],
        "journal": journal,
        "publication_date": publication_date,
        "abstract": abstract,
        "url": item.get("url", "") or (f"https://doi.org/{doi}" if doi else ""),
        "pdf_url": open_pdf.get("url", ""),
        "citation_count": item.get("citationCount", 0),
        "influential_citation_count": item.get("influentialCitationCount", 0),
        "reference_count": item.get("referenceCount", 0),
        "references": [],
        "tags": classify(" ".join([title, abstract, journal])),
    }


def classify(text_value: str) -> list[str]:
    haystack = f" {text_value.lower()} "
    tags = [tag for tag, needles in TAG_RULES.items() if any(needle in haystack for needle in needles)]
    if "carbon" in tags or "nutrient" in tags or "oxygen" in tags:
        tags.append("metabolism")
    return sorted(set(tags)) or ["metabolism"]


def is_relevant(paper: dict[str, Any]) -> bool:
    text_value = " ".join([paper.get("title", ""), paper.get("abstract", ""), paper.get("journal", "")]).lower()
    if any(term in text_value for term in NOISE_TERMS):
        return False
    tags = set(paper.get("tags") or classify(text_value))
    has_system = bool(tags & {"river", "lake", "pond", "ditch", "wetland", "sediment"})
    has_process = bool(tags & {"oxygen", "metabolism", "carbon", "nutrient", "microbe", "greenhouse"})
    return bool(paper.get("title")) and has_system and has_process


def enrich_query_tags(paper: dict[str, Any], query_tags: list[str]) -> dict[str, Any]:
    paper["tags"] = sorted(set(paper.get("tags", []) + query_tags))
    return paper


def deduplicate(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for paper in sorted(papers, key=lambda item: item.get("publication_date", ""), reverse=True):
        key = paper_key(paper)
        if key in seen:
            continue
        seen.add(key)
        unique.append(paper)
    return unique


def paper_key(paper: dict[str, Any]) -> str:
    if paper.get("doi"):
        return f"doi:{paper['doi'].lower()}"
    title = " ".join((paper.get("title") or "").lower().split())
    return f"title:{title[:160]}"


def normalize_doi(value: Any) -> str:
    if not value:
        return ""
    return str(value).replace("https://doi.org/", "").replace("http://dx.doi.org/", "").strip()


def load_existing_papers(output: Path) -> list[dict[str, Any]]:
    if not output.exists():
        return []
    return json.loads(output.read_text(encoding="utf-8")).get("papers", [])


def write_data(papers: list[dict[str, Any]], output: Path, sources: list[str]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "queries": SEARCH_QUERIES,
        "papers": papers,
    }
    json_text = json.dumps(payload, ensure_ascii=False, indent=2)
    output.write_text(json_text, encoding="utf-8")
    output.with_suffix(".js").write_text(f"window.PAPER_TRACKER_DATA = {json_text};\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retmax", type=int, default=160)
    parser.add_argument("--email", default=None)
    parser.add_argument("--output", default="data/papers.json")
    parser.add_argument("--sources", default="semantic", help="Only Semantic Scholar is supported; kept for CLI compatibility.")
    parser.add_argument("--semantic-api-key", default=semantic_api_key_from_env())
    parser.add_argument("--merge-existing", action="store_true")
    parser.add_argument("--query-limit", type=int, default=120)
    args = parser.parse_args()

    output = Path(args.output)
    all_papers: list[dict[str, Any]] = []
    try:
        all_papers.extend(fetch_semantic_scholar(args.retmax, args.email, args.semantic_api_key, args.query_limit))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
        print(f"Semantic Scholar fetch failed; keeping existing data if available. {error}")
    if args.merge_existing:
        all_papers.extend(load_existing_papers(output))

    papers = deduplicate(all_papers)[: args.retmax]
    if not papers and output.exists():
        print("No fresh papers were fetched; keeping the existing data file.")
        return
    source_labels = ["Semantic Scholar"]
    write_data(papers, output, source_labels)
    print(f"Updated {len(papers)} papers from {', '.join(source_labels)} at {output}")


if __name__ == "__main__":
    main()
