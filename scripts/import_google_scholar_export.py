#!/usr/bin/env python3
"""Import manually exported Google Scholar results into data/papers.json.

This script is for user-initiated exports from browser tools such as
google-scholar-assistant or Google Scholar citation downloads. It does not
scrape Google Scholar.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from update_papers import classify, deduplicate, normalize_doi


CSV_ALIASES = {
    "title": ["title", "题名", "标题", "paper title", "文献标题"],
    "authors": ["authors", "author", "作者"],
    "journal": ["journal", "source", "publication", "venue", "期刊", "来源", "出版物"],
    "year": ["year", "年份", "publication year"],
    "publication_date": ["publication_date", "date", "published", "发表日期", "出版日期"],
    "doi": ["doi"],
    "url": ["url", "link", "链接"],
    "abstract": ["abstract", "摘要"],
    "citation_count": ["cites", "citations", "citation_count", "被引", "引用", "引用次数"],
}

RIS_FIELDS = {
    "TI": "title",
    "T1": "title",
    "AU": "authors",
    "A1": "authors",
    "JO": "journal",
    "JF": "journal",
    "JA": "journal",
    "T2": "journal",
    "PY": "year",
    "Y1": "publication_date",
    "DO": "doi",
    "UR": "url",
    "AB": "abstract",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("export_file", help="CSV or RIS exported manually from Google Scholar / browser extension")
    parser.add_argument("--output", default="data/papers.json")
    parser.add_argument("--source-name", default="Google Scholar manual export")
    args = parser.parse_args()

    export_path = Path(args.export_file)
    output = Path(args.output)
    existing = load_existing(output)

    if export_path.suffix.lower() == ".ris":
        imported = parse_ris(export_path, args.source_name)
    else:
        imported = parse_csv(export_path, args.source_name)

    papers = deduplicate([*imported, *existing.get("papers", [])])
    sources = sorted({paper.get("source", "") for paper in papers if paper.get("source")})
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "queries": existing.get("queries", []),
        "papers": papers,
    }
    write_payload(output, payload)
    print(f"Imported {len(imported)} Google Scholar records; library now has {len(papers)} papers.")


def parse_csv(path: Path, source_name: str) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [csv_row_to_paper(row, source_name) for row in reader if pick(row, "title")]


def csv_row_to_paper(row: dict[str, str], source_name: str) -> dict[str, Any]:
    title = pick(row, "title")
    abstract = pick(row, "abstract")
    journal = pick(row, "journal")
    doi = normalize_doi(pick(row, "doi"))
    url = pick(row, "url") or (f"https://doi.org/{doi}" if doi else "")
    return normalize_paper(
        {
            "id": f"{source_name}:{doi or title[:120]}",
            "source": source_name,
            "pmid": "",
            "doi": doi,
            "title": title,
            "authors": parse_authors(pick(row, "authors")),
            "journal": journal,
            "publication_date": parse_date(pick(row, "publication_date"), pick(row, "year")),
            "abstract": abstract,
            "url": url,
            "pdf_url": "",
            "citation_count": parse_int(pick(row, "citation_count")),
            "influential_citation_count": 0,
            "reference_count": 0,
            "references": [],
            "tags": classify(" ".join([title, abstract, journal])),
        }
    )


def parse_ris(path: Path, source_name: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    current: dict[str, Any] = {}

    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r"^([A-Z0-9]{2})  - (.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        if key == "TY":
            current = {"authors": []}
            continue
        if key == "ER":
            paper = ris_record_to_paper(current, source_name)
            if paper.get("title"):
                records.append(paper)
            current = {}
            continue
        field = RIS_FIELDS.get(key)
        if not field:
            continue
        if field == "authors":
            current.setdefault("authors", []).append(value.strip())
        else:
            current[field] = value.strip()

    return records


def ris_record_to_paper(record: dict[str, Any], source_name: str) -> dict[str, Any]:
    title = record.get("title", "")
    abstract = record.get("abstract", "")
    journal = record.get("journal", "")
    doi = normalize_doi(record.get("doi", ""))
    url = record.get("url", "") or (f"https://doi.org/{doi}" if doi else "")
    return normalize_paper(
        {
            "id": f"{source_name}:{doi or title[:120]}",
            "source": source_name,
            "pmid": "",
            "doi": doi,
            "title": title,
            "authors": record.get("authors", []),
            "journal": journal,
            "publication_date": parse_date(record.get("publication_date", ""), record.get("year", "")),
            "abstract": abstract,
            "url": url,
            "pdf_url": "",
            "citation_count": 0,
            "influential_citation_count": 0,
            "reference_count": 0,
            "references": [],
            "tags": classify(" ".join([title, abstract, journal])),
        }
    )


def normalize_paper(paper: dict[str, Any]) -> dict[str, Any]:
    paper["tags"] = sorted(set(paper.get("tags", []) + ["google-scholar"]))
    return paper


def pick(row: dict[str, str], field: str) -> str:
    normalized = {key.strip().lower(): value.strip() for key, value in row.items() if key and value}
    for alias in CSV_ALIASES[field]:
        if alias.lower() in normalized:
            return normalized[alias.lower()]
    return ""


def parse_authors(value: str) -> list[str]:
    if not value:
        return []
    separator = ";" if ";" in value else ","
    return [author.strip() for author in value.split(separator) if author.strip()]


def parse_date(date_value: str, year: str) -> str:
    if date_value:
        return date_value
    year_match = re.search(r"\d{4}", year or "")
    return f"{year_match.group(0)}-01-01" if year_match else ""


def parse_int(value: str) -> int:
    try:
        return int(value.replace(",", ""))
    except ValueError:
        return 0


def load_existing(output: Path) -> dict[str, Any]:
    if output.exists():
        return json.loads(output.read_text(encoding="utf-8"))
    return {"papers": [], "queries": []}


def write_payload(output: Path, payload: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    json_text = json.dumps(payload, ensure_ascii=False, indent=2)
    output.write_text(json_text, encoding="utf-8")
    output.with_suffix(".js").write_text(f"window.PAPER_TRACKER_DATA = {json_text};\n", encoding="utf-8")


if __name__ == "__main__":
    main()
