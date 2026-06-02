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


SEMANTIC_SCHOLAR_BULK_SEARCH_BASE = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
SEMANTIC_SCHOLAR_BATCH_BASE = "https://api.semanticscholar.org/graph/v1/paper/batch"

BULK_FIELDS = ",".join(
    [
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
    ]
)

BATCH_FIELDS = ",".join(
    [
        BULK_FIELDS,
        "publicationTypes",
        "fieldsOfStudy",
        "s2FieldsOfStudy",
        "tldr",
    ]
)

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
            return value.strip()
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
    "estuary",
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
    "metabolism model",
    "microbial metabolism",
    "biofilm metabolism",
]

SEED_QUERIES = [
    "stream metabolism dissolved oxygen",
    "lake metabolism dissolved oxygen",
    "whole lake metabolism",
    "river ecosystem metabolism",
    "freshwater ecosystem metabolism oxygen",
    "aquatic ecosystem metabolism oxygen",
    '"ecosystem metabolism" freshwater',
    '"aquatic ecosystem metabolism"',
    '"stream metabolism" "dissolved oxygen"',
    '"lake metabolism" "dissolved oxygen"',
    '"gross primary production" "ecosystem respiration" freshwater',
    '"net ecosystem production" aquatic',
    '"dissolved oxygen" "ecosystem respiration" stream',
    '"reaeration" "stream metabolism"',
    '"stable isotopes" "aquatic metabolism"',
    '"oxygen isotopes" "ecosystem metabolism"',
    '"Bayesian" "stream metabolism"',
]

SEARCH_QUERIES = SEED_QUERIES + [
    f'"{water}" "{process}"'
    for water in WATER_TERMS
    for process in METABOLISM_TERMS
]

BULK_SORTS = ["citationCount:desc", "publicationDate:desc"]

TAG_RULES = {
    "river": [" river", " rivers", " stream", " streams", " creek", " creeks", " hyporheic"],
    "lake": [" lake", " lakes", " reservoir", " reservoirs"],
    "pond": [" pond", " ponds", " small water bod"],
    "ditch": [" ditch", " ditches", " canal", " canals", " tidal creek", " tidal creeks"],
    "wetland": [" wetland", " wetlands", " marsh", " mangrove", " saltmarsh", " estuary"],
    "sediment": [" sediment", " sediments", " benthic", " hyporheic"],
    "oxygen": [" dissolved oxygen", " oxygen dynamics", " reaeration", " reaeration", "oxygen time series"],
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
    "isotope": [" isotope", " isotopes", " isotopic", " 18o", " oxygen-18", " stable isotope", " isotope tracing"],
    "model": [" model", " modeling", " modelling", " bayesian", " inverse model", " reactive transport", " odem"],
    "sensor": [" sensor", " sensors", " high frequency", " high-frequency", " time series", " logger", " diel"],
    "microbe": [" microbial", " bacteria", " bacterial", " biofilm", " periphyton", " decomposition"],
}

NOISE_TERMS = [
    "patient",
    "clinical",
    "vaccine",
    "cancer",
    "tumor",
    "mouse",
    "mice",
    "drinking water",
    "water quality index",
    "water quality prediction",
    "permissible limits",
    "heavy metal",
    "heavy metals",
    "pharmaceutical",
    "pesticide",
    "wastewater treatment",
    "wastewater",
    "treatment plant",
    "ozone",
    "dielectric barrier discharge",
    "remote sensing",
    "spectral indices",
    "machine learning",
    "decision tree",
    "random forest",
    "support vector",
    "deep learning",
    "climate reconstruction",
    "late pleistocene",
    "south china sea",
    "gulf of mexico",
    "mediterranean",
    "black sea",
    "ocean",
    "marine",
    "seawater",
    "greenhouse gas",
    "greenhouse gases",
    "methane emission",
    "methane emissions",
    "co2 emission",
    "co2 emissions",
    "n2o emission",
    "n2o emissions",
]

GREENHOUSE_GAS_TERMS = [
    "greenhouse gas",
    "greenhouse gases",
    "ghg",
    "methane emission",
    "methane emissions",
    "ch4 emission",
    "ch4 emissions",
    "carbon dioxide emission",
    "carbon dioxide emissions",
    "co2 emission",
    "co2 emissions",
    "nitrous oxide",
    "n2o emission",
    "n2o emissions",
    "gas emission",
    "gas emissions",
    "carbon flux",
    "carbon fluxes",
]

CORE_METABOLISM_TERMS = [
    "ecosystem metabolism",
    "whole-stream metabolism",
    "whole stream metabolism",
    "whole-lake metabolism",
    "whole lake metabolism",
    "aquatic metabolism",
    "stream metabolism",
    "lake metabolism",
    "gross primary production",
    "ecosystem respiration",
    "net ecosystem production",
    "net ecosystem metabolism",
    "gpp",
    " er ",
    " nep",
    "reaeration",
    "oxygen time series",
    "diel oxygen",
    "dissolved oxygen time series",
]

CORE_ENTRY_TERMS = [
    "ecosystem metabolism",
    "whole-stream metabolism",
    "whole stream metabolism",
    "whole-lake metabolism",
    "whole lake metabolism",
    "aquatic metabolism",
    "stream metabolism",
    "river metabolism",
    "lake metabolism",
    "pond metabolism",
    "reservoir metabolism",
    "metabolism estimates",
    "metabolism estimate",
    "metabolism model",
    "metabolic regime",
    "gross primary production",
    "ecosystem respiration",
    "net ecosystem production",
    "net ecosystem metabolism",
    "daily metabolism",
    "diel metabolism",
    "metabolic balance",
    "free-water metabolism",
    "free water metabolism",
]

SUPPORT_ENTRY_TERMS = [
    "gpp",
    " er ",
    " nep",
    "gross production",
    "primary production",
    "community respiration",
    "benthic respiration",
    "aerobic respiration",
    "oxygen budget",
    "oxygen budgets",
    "diel oxygen",
    "diel dissolved oxygen",
    "oxygen time series",
    "dissolved oxygen time series",
    "free-water oxygen",
    "free water oxygen",
    "open-channel oxygen",
    "open channel oxygen",
    "reaeration",
]

METHOD_TERMS = [
    "stable isotope",
    "oxygen isotope",
    "isotope tracing",
    "bayesian",
    "inverse model",
    "metabolism model",
    "reactive transport model",
    "high frequency oxygen",
    "high-frequency oxygen",
    "sensor monitoring",
    "diel",
    "high-frequency",
    "high frequency",
    "logger",
    "open-channel",
    "single-station",
    "two-station",
]


def request_json(url: str, params: dict[str, str | int], email: str | None = None, api_key: str | None = None) -> dict[str, Any]:
    headers = {"User-Agent": build_user_agent(email)}
    if api_key:
        headers["x-api-key"] = api_key.strip()
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


def post_json(
    url: str,
    params: dict[str, str | int],
    payload: dict[str, Any],
    email: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    headers = {"User-Agent": build_user_agent(email), "Content-Type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key.strip()
    request = urllib.request.Request(
        f"{url}?{urllib.parse.urlencode(params)}",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=70) as response:
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


def fetch_semantic_scholar(
    retmax: int,
    email: str | None,
    api_key: str | None,
    query_limit: int | None = None,
    target_records: int | None = None,
    existing_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    queries = SEARCH_QUERIES[:query_limit] if query_limit else SEARCH_QUERIES
    per_query = 1000
    target = target_records or retmax
    papers: list[dict[str, Any]] = []
    seen_ids: set[str] = set(existing_ids or set())
    for query in queries:
        for sort in BULK_SORTS:
            token = ""
            while len(papers) < target:
                params: dict[str, str | int] = {"query": query, "limit": per_query, "fields": BULK_FIELDS, "sort": sort}
                if token:
                    params["token"] = token
                try:
                    data = request_json(SEMANTIC_SCHOLAR_BULK_SEARCH_BASE, params, email, api_key)
                except urllib.error.HTTPError as error:
                    if error.code == 400 and "sort" in params:
                        params.pop("sort", None)
                        data = request_json(SEMANTIC_SCHOLAR_BULK_SEARCH_BASE, params, email, api_key)
                    elif error.code == 429:
                        return [paper for paper in papers if paper and is_relevant(paper)]
                    else:
                        raise
                query_tags = classify(query)
                for item in data.get("data", []):
                    paper_id = item.get("paperId", "")
                    if paper_id and paper_id in seen_ids:
                        continue
                    if paper_id:
                        seen_ids.add(paper_id)
                    paper = parse_semantic_paper(item)
                    if paper and is_relevant(paper):
                        papers.append(enrich_query_tags(paper, query_tags))
                token = data.get("token") or ""
                if not token or len(papers) >= target:
                    break
                time.sleep(0.25 if api_key else 1.0)
        query_tags = classify(query)
        if len(papers) >= target:
            break
        time.sleep(0.35 if api_key else 1.05)
    return batch_fill_semantic_details(papers, email, api_key)


def batch_fill_semantic_details(papers: list[dict[str, Any]], email: str | None, api_key: str | None) -> list[dict[str, Any]]:
    id_to_paper = {paper.get("id"): paper for paper in papers if paper.get("id")}
    ids = list(id_to_paper)
    for start in range(0, len(ids), 500):
        chunk = ids[start : start + 500]
        data = post_json(SEMANTIC_SCHOLAR_BATCH_BASE, {"fields": BATCH_FIELDS}, {"ids": chunk}, email, api_key)
        for item in data:
            if not item:
                continue
            paper = id_to_paper.get(item.get("paperId"))
            if paper:
                merge_semantic_detail(paper, item)
        time.sleep(0.25 if api_key else 1.0)
    return papers


def merge_semantic_detail(paper: dict[str, Any], item: dict[str, Any]) -> None:
    updated = parse_semantic_paper(item)
    for key, value in updated.items():
        if value not in ("", [], None):
            paper[key] = value
    s2 = paper.setdefault("semantic_scholar", {})
    s2.update(
        {
            "paper_id": item.get("paperId") or paper.get("id", ""),
            "tldr": (item.get("tldr") or {}).get("text", ""),
            "fields_of_study": item.get("fieldsOfStudy") or [],
            "s2_fields_of_study": item.get("s2FieldsOfStudy") or [],
            "publication_types": item.get("publicationTypes") or [],
            "external_ids": item.get("externalIds") or {},
        }
    )
    paper["tags"] = sorted(set((paper.get("tags") or []) + classify(" ".join([paper.get("title", ""), paper.get("abstract", ""), paper.get("journal", "")]))))


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
    if has_core_entry(haystack):
        tags.append("metabolism")
    return sorted(set(tags)) or ["metabolism"]


def is_relevant(paper: dict[str, Any]) -> bool:
    text_value = " ".join([paper.get("title", ""), paper.get("abstract", ""), paper.get("journal", "")]).lower()
    if any(term in text_value for term in NOISE_TERMS):
        return False
    if is_greenhouse_gas_only(text_value):
        return False
    tags = set(classify(text_value))
    has_system = bool(tags & {"river", "lake", "pond", "ditch", "wetland", "sediment"})
    return bool(paper.get("title")) and has_system and has_core_entry(f" {text_value} ")


def has_core_entry(text_value: str) -> bool:
    return any(term in text_value for term in CORE_ENTRY_TERMS) or any(term in text_value for term in SUPPORT_ENTRY_TERMS)


def is_greenhouse_gas_only(text_value: str) -> bool:
    has_greenhouse_focus = any(term in text_value for term in GREENHOUSE_GAS_TERMS)
    if not has_greenhouse_focus:
        return False
    has_metabolism_focus = any(term in f" {text_value} " for term in CORE_METABOLISM_TERMS)
    has_method_focus = any(term in text_value for term in METHOD_TERMS)
    return not (has_metabolism_focus or has_method_focus)


def enrich_query_tags(paper: dict[str, Any], query_tags: list[str]) -> dict[str, Any]:
    paper["tags"] = sorted(set(paper.get("tags", []) + query_tags))
    return paper


def deduplicate(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for paper in sorted(papers, key=paper_selection_score, reverse=True):
        key = paper_key(paper)
        if key in seen:
            continue
        seen.add(key)
        unique.append(paper)
    return unique


def paper_selection_score(paper: dict[str, Any]) -> tuple[int, int, str]:
    tags = set(paper.get("tags") or [])
    method_bonus = 150 * len(tags & {"oxygen", "isotope", "model", "sensor", "microbe"})
    system_bonus = 100 * len(tags & {"river", "lake", "pond", "ditch", "wetland", "sediment"})
    citation_score = min(int(paper.get("citation_count") or 0), 20000)
    influential_score = 5 * min(int(paper.get("influential_citation_count") or 0), 5000)
    return (citation_score + influential_score + method_bonus + system_bonus, len(tags), paper.get("publication_date", ""))


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


def existing_paper_ids(papers: list[dict[str, Any]]) -> set[str]:
    return {paper["id"] for paper in papers if paper.get("id")}


def write_data(
    papers: list[dict[str, Any]],
    output: Path,
    sources: list[str],
    update_status: dict[str, Any] | None = None,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "queries": SEARCH_QUERIES,
        "update_status": update_status or {},
        "papers": papers,
    }
    json_text = json.dumps(payload, ensure_ascii=False, indent=2)
    output.write_text(json_text, encoding="utf-8")
    output.with_suffix(".js").write_text(f"window.PAPER_TRACKER_DATA = {json_text};\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retmax", type=int, default=5000)
    parser.add_argument("--email", default=os.environ.get("CONTACT_EMAIL"))
    parser.add_argument("--output", default="data/papers.json")
    parser.add_argument("--sources", default="semantic", help="Only Semantic Scholar is supported; kept for CLI compatibility.")
    parser.add_argument("--semantic-api-key", default=semantic_api_key_from_env())
    parser.add_argument("--merge-existing", action="store_true")
    parser.add_argument("--query-limit", type=int, default=None)
    parser.add_argument(
        "--refresh-limit",
        type=int,
        default=800,
        help="Maximum fresh Semantic Scholar records to fetch when an existing cache is already present.",
    )
    args = parser.parse_args()

    output = Path(args.output)
    existing_papers = load_existing_papers(output) if args.merge_existing else []
    existing_count = len(existing_papers)
    fetch_target = args.retmax if existing_count < args.retmax else args.refresh_limit
    all_papers: list[dict[str, Any]] = []
    fetch_error = ""
    try:
        all_papers.extend(
            fetch_semantic_scholar(
                args.retmax,
                args.email,
                args.semantic_api_key,
                args.query_limit,
                target_records=fetch_target,
                existing_ids=existing_paper_ids(existing_papers),
            )
        )
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
        fetch_error = f"{type(error).__name__}: {error}"
        print(f"Semantic Scholar fetch failed; keeping existing data if available. {fetch_error}")
    fresh_count = len(all_papers)
    if args.merge_existing:
        all_papers.extend(existing_papers)

    papers = deduplicate(all_papers)[: args.retmax]
    if not papers and output.exists():
        print("No fresh papers were fetched; keeping the existing data file.")
        return
    source_labels = ["Semantic Scholar"]
    update_status = {
        "semantic_api_key_detected": bool(args.semantic_api_key),
        "fresh_records_before_merge": fresh_count,
        "total_records_after_merge": len(papers),
        "query_limit": args.query_limit,
        "retmax": args.retmax,
        "existing_records_before_update": existing_count,
        "fresh_fetch_target": fetch_target,
        "cache_mode": "merge existing papers; fetch only new candidates when cache is warm",
        "search_mode": "Semantic Scholar paper/search/bulk",
        "batch_detail_fill": True,
        "error": fetch_error,
    }
    write_data(papers, output, source_labels, update_status)
    print(f"Updated {len(papers)} papers from {', '.join(source_labels)} at {output}")


if __name__ == "__main__":
    main()
