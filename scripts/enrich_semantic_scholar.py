#!/usr/bin/env python3
"""Enrich existing tracker records with Semantic Scholar detail and graph data."""

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


BASE = "https://api.semanticscholar.org/graph/v1"


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/papers.json")
    parser.add_argument("--output", default="data/papers.json")
    parser.add_argument("--semantic-api-key", default=semantic_api_key_from_env())
    parser.add_argument("--limit", type=int, default=40, help="Maximum papers to enrich in one run.")
    parser.add_argument("--edge-limit", type=int, default=12, help="References and citations to keep per paper.")
    args = parser.parse_args()

    if not args.semantic_api_key:
        raise SystemExit("Set SEMANTIC_SCHOLAR_API_KEY or S2_API_KEY, or pass --semantic-api-key.")

    input_path = Path(args.input)
    output_path = Path(args.output)
    payload = json.loads(input_path.read_text(encoding="utf-8"))

    enriched = 0
    for paper in payload.get("papers", []):
        if enriched >= args.limit:
            break
        if paper.get("source") != "Semantic Scholar" or not paper.get("id"):
            continue
        enrich_paper(paper, args.semantic_api_key, args.edge_limit)
        enriched += 1
        time.sleep(0.12)

    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    payload["sources"] = ["Semantic Scholar"]
    payload["semantic_scholar_enriched"] = True
    json_text = json.dumps(payload, ensure_ascii=False, indent=2)
    output_path.write_text(json_text, encoding="utf-8")
    output_path.with_suffix(".js").write_text(f"window.PAPER_TRACKER_DATA = {json_text};\n", encoding="utf-8")
    print(f"Enriched {enriched} papers with Semantic Scholar detail and graph data.")


def enrich_paper(paper: dict[str, Any], api_key: str, edge_limit: int) -> None:
    paper_id = paper["id"]
    details = request_json(
        f"{BASE}/paper/{urllib.parse.quote(paper_id)}",
        {
            "fields": ",".join(
                [
                    "paperId",
                    "title",
                    "abstract",
                    "year",
                    "venue",
                    "publicationDate",
                    "publicationTypes",
                    "fieldsOfStudy",
                    "s2FieldsOfStudy",
                    "tldr",
                    "externalIds",
                    "openAccessPdf",
                    "citationCount",
                    "influentialCitationCount",
                    "referenceCount",
                    "authors.authorId",
                    "authors.name",
                    "authors.url",
                ]
            )
        },
        api_key,
    )
    references = request_edge_list(paper_id, "references", api_key, edge_limit)
    citations = request_edge_list(paper_id, "citations", api_key, edge_limit)

    paper["semantic_scholar"] = {
        "paper_id": details.get("paperId") or paper_id,
        "tldr": (details.get("tldr") or {}).get("text", ""),
        "fields_of_study": details.get("fieldsOfStudy") or [],
        "s2_fields_of_study": details.get("s2FieldsOfStudy") or [],
        "publication_types": details.get("publicationTypes") or [],
        "external_ids": details.get("externalIds") or {},
        "authors": details.get("authors") or [],
        "references": references,
        "citations": citations,
    }
    paper["citation_count"] = details.get("citationCount", paper.get("citation_count", 0))
    paper["influential_citation_count"] = details.get(
        "influentialCitationCount", paper.get("influential_citation_count", 0)
    )
    paper["reference_count"] = details.get("referenceCount", paper.get("reference_count", 0))
    if details.get("openAccessPdf", {}).get("url"):
        paper["pdf_url"] = details["openAccessPdf"]["url"]
    if details.get("abstract"):
        paper["abstract"] = details["abstract"]


def request_edge_list(paper_id: str, edge: str, api_key: str, limit: int) -> list[dict[str, Any]]:
    data = request_json(
        f"{BASE}/paper/{urllib.parse.quote(paper_id)}/{edge}",
        {
            "limit": limit,
            "fields": "paperId,title,year,venue,authors,citationCount,influentialCitationCount,url",
        },
        api_key,
    )
    key = "citingPaper" if edge == "citations" else "citedPaper"
    return [normalize_edge(item.get(key) or {}) for item in data.get("data", []) if item.get(key)]


def normalize_edge(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "paper_id": item.get("paperId", ""),
        "title": item.get("title", ""),
        "year": item.get("year", ""),
        "venue": item.get("venue", ""),
        "authors": [author.get("name", "") for author in item.get("authors", []) if author.get("name")][:3],
        "citation_count": item.get("citationCount", 0),
        "influential_citation_count": item.get("influentialCitationCount", 0),
        "url": item.get("url", ""),
    }


def request_json(url: str, params: dict[str, str | int], api_key: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{url}?{urllib.parse.urlencode(params)}",
        headers={"x-api-key": api_key.strip(), "User-Agent": "aquatic-metabolism-tracker/1.0"},
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt < 2:
                time.sleep(int(error.headers.get("Retry-After", "8")) + 2)
                continue
            raise


if __name__ == "__main__":
    main()
