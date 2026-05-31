#!/usr/bin/env python3
"""Import manually exported seed papers into data/papers.json.

This is intended for Google Scholar / Publish or Perish CSV exports, or any
spreadsheet with common bibliographic columns.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parent))
from update_papers import classify, deduplicate, normalize_doi  # noqa: E402


FIELD_ALIASES = {
    "title": ["title", "题名", "标题"],
    "authors": ["authors", "author", "作者"],
    "journal": ["source", "publication", "journal", "venue", "期刊", "来源"],
    "year": ["year", "年份"],
    "publication_date": ["publication_date", "date", "published", "发表日期"],
    "doi": ["doi"],
    "url": ["url", "link", "链接"],
    "abstract": ["abstract", "摘要"],
    "citation_count": ["cites", "citations", "citation_count", "被引", "引用"],
}


def pick(row: dict[str, str], field: str) -> str:
    normalized = {key.strip().lower(): value.strip() for key, value in row.items() if key}
    for alias in FIELD_ALIASES[field]:
        if alias.lower() in normalized:
            return normalized[alias.lower()]
    return ""


def parse_authors(value: str) -> list[str]:
    if not value:
        return []
    separator = ";" if ";" in value else ","
    return [author.strip() for author in value.split(separator) if author.strip()]


def parse_date(row: dict[str, str]) -> str:
    date_value = pick(row, "publication_date")
    if date_value:
        return date_value
    year = pick(row, "year")
    return f"{year}-01-01" if year else ""


def parse_int(value: str) -> int:
    try:
        return int(value.replace(",", ""))
    except ValueError:
        return 0


def row_to_paper(row: dict[str, str], source_name: str) -> dict[str, Any]:
    title = pick(row, "title")
    abstract = pick(row, "abstract")
    journal = pick(row, "journal")
    doi = normalize_doi(pick(row, "doi"))
    tags = classify(" ".join([title, abstract, journal]))
    return {
        "id": f"{source_name}:{doi or title[:120]}",
        "source": source_name,
        "pmid": "",
        "doi": doi,
        "title": title,
        "authors": parse_authors(pick(row, "authors")),
        "journal": journal,
        "publication_date": parse_date(row),
        "abstract": abstract,
        "url": pick(row, "url") or (f"https://doi.org/{doi}" if doi else ""),
        "pdf_url": "",
        "citation_count": parse_int(pick(row, "citation_count")),
        "tags": tags,
    }


def load_existing(output: Path) -> dict[str, Any]:
    if output.exists():
        return json.loads(output.read_text(encoding="utf-8"))
    return {"papers": []}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument("--output", default="data/papers.json")
    parser.add_argument("--source-name", default="Google Scholar seed")
    args = parser.parse_args()

    csv_path = Path(args.csv_file)
    output = Path(args.output)
    existing = load_existing(output)

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        imported = [row_to_paper(row, args.source_name) for row in reader]

    papers = deduplicate([*imported, *existing.get("papers", [])])
    sources = sorted({paper.get("source", "") for paper in papers if paper.get("source")})
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "queries": existing.get("queries", []),
        "papers": papers,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Imported {len(imported)} seed papers; library now has {len(papers)} papers.")


if __name__ == "__main__":
    main()
