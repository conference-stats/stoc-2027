import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from html.parser import HTMLParser
from itertools import combinations
from pathlib import Path
from statistics import mean, median, pstdev, quantiles
from unicodedata import normalize


class ReportParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.payloads = {}
        self.comparisons = []
        self.payload_id = None
        self.article = None
        self.comparison_table = False
        self.in_heading = False
        self.current_row = None
        self.cell = 0

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        classes = attrs.get("class", "").split()
        if tag == "script" and attrs.get("type") == "application/json":
            self.payload_id = attrs["id"]
            self.payloads[self.payload_id] = ""
        if tag == "article":
            self.article = {"title": "", "papers": []}
        if self.article is None:
            return
        if tag == "h4":
            self.in_heading = True
        if tag == "table" and "comparison-table" in classes:
            self.comparison_table = True
        if not self.comparison_table:
            return
        if tag == "tr":
            self.current_row = {}
            self.cell = 0
        if self.current_row is None:
            return
        if tag == "td":
            self.cell += 1
        if tag == "a" and self.cell in {1, 2}:
            href = attrs.get("href", "")
            match = re.fullmatch(r"https://(?:stoc2027\.sigact-ec\.workers\.dev/submissions|github\.com/sigact-stoc/stoc2027/releases/download/papers-[12])/(\d+)\.pdf(?:#page=(\d+))?", href)
            if match:
                if self.cell == 1:
                    self.current_row["id"] = int(match[1])
                if match[2]:
                    self.current_row["method_page"] = int(match[2])
        if tag == "span" and self.cell == 3 and "status" in classes:
            self.current_row["status"] = next((c for c in classes if c != "status"), "")

    def handle_endtag(self, tag):
        if tag == "script":
            self.payload_id = None
        if tag == "h4":
            self.in_heading = False
        if tag == "tr" and self.comparison_table and self.current_row is not None:
            if self.current_row:
                self.article["papers"].append(self.current_row)
            self.current_row = None
        if tag == "table":
            self.comparison_table = False
        if tag == "article" and self.article is not None:
            if self.article["papers"]:
                self.comparisons.append(self.article)
            self.article = None

    def handle_data(self, value):
        if self.payload_id is not None:
            self.payloads[self.payload_id] += value
        if self.in_heading and self.article is not None:
            self.article["title"] += value


def author_name(value):
    return " ".join(normalize("NFC", value).split())


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def indexed(rows, label):
    result = {row["id"]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"Duplicate paper ID in {label}")
    return result


def verify_snapshot(by_id, manifest, pdf_dir):
    snapshots = indexed(manifest["papers"], "PDF manifest")
    problems = []
    verified = 0
    for label, ids in (("missing from manifest", by_id.keys() - snapshots.keys()),
                       ("missing from catalog", snapshots.keys() - by_id.keys())):
        problems.extend(f"Paper #{identifier}: {label}" for identifier in sorted(ids))
    for identifier in sorted(by_id.keys() & snapshots.keys()):
        row = by_id[identifier]
        snapshot = snapshots[identifier]
        if row["url"] != snapshot["original"]:
            problems.append(f"Paper #{identifier}: original URL differs")
        if row["pages"] != snapshot["pages"]:
            problems.append(f"Paper #{identifier}: catalog has {row['pages']} pages, manifest has {snapshot['pages']}")
        if not re.fullmatch(r"[a-f0-9]{64}", snapshot["sha256"]):
            problems.append(f"Paper #{identifier}: invalid manifest checksum")
        if not isinstance(snapshot["bytes"], int) or snapshot["bytes"] <= 0:
            problems.append(f"Paper #{identifier}: invalid manifest byte count")
        if pdf_dir is None:
            continue
        path = pdf_dir / f"{identifier}.pdf"
        if not path.is_file():
            problems.append(f"Paper #{identifier}: local PDF missing")
        elif path.stat().st_size != snapshot["bytes"]:
            problems.append(f"Paper #{identifier}: local PDF byte count differs")
        elif sha256_file(path) != snapshot["sha256"]:
            problems.append(f"Paper #{identifier}: local PDF checksum differs")
        else:
            verified += 1
    if problems:
        raise ValueError("\n".join(problems))
    return {
        "date": manifest["date"],
        "matched_papers": len(snapshots),
        "manifest_bytes": sum(s["bytes"] for s in snapshots.values()),
        "manifest_distinct_pdf_hashes": len({s["sha256"] for s in snapshots.values()}),
        "local_pdfs_verified": verified if pdf_dir is not None else None,
    }


def paper_lengths(papers):
    pages = [paper["pages"] for paper in papers if paper["pages"]]
    edges = [(1, 15), (16, 25), (26, 40), (41, 60), (61, 100), (101, None)]
    return {
        "papers": len(pages),
        "pages_total": sum(pages),
        "minimum": min(pages),
        "median": median(pages),
        "mean": mean(pages),
        "population_standard_deviation": pstdev(pages),
        "quartiles_inclusive": quantiles(pages, n=4, method="inclusive"),
        "maximum": max(pages),
        "length_rank": sorted(
            ({"id": paper["id"], "pages": paper["pages"]} for paper in papers if paper["pages"]),
            key=lambda row: (-row["pages"], row["id"]),
        ),
        "histogram": [
            {"minimum": low, "maximum": high,
             "papers": sum(value >= low and (high is None or value <= high) for value in pages)}
            for low, high in edges
        ],
    }


def collaboration(papers):
    sizes, appearances, pair_counts, roster_counts = Counter(), Counter(), Counter(), Counter()
    neighbors = defaultdict(set)
    for paper in papers:
        authors = sorted({author_name(author) for author in paper["authors"]})
        sizes[len(paper["authors"])] += 1
        appearances.update(authors)
        for author in authors:
            neighbors[author]
        if len(authors) > 1:
            roster_counts[tuple(authors)] += 1
        for left, right in combinations(authors, 2):
            pair_counts[left, right] += 1
            neighbors[left].add(right)
            neighbors[right].add(left)
    unvisited = set(neighbors)
    component_sizes = []
    while unvisited:
        root = unvisited.pop()
        pending = [root]
        size = 0
        while pending:
            size += 1
            fresh = neighbors[pending.pop()] & unvisited
            unvisited.difference_update(fresh)
            pending.extend(fresh)
        component_sizes.append(size)
    return {
        "author_positions": sum(size * count for size, count in sizes.items()),
        "distinct_display_names": len(appearances),
        "team_sizes": sizes,
        "name_appearances": Counter(appearances.values()),
        "unique_coauthor_pairs": len(pair_counts),
        "recurring_coauthor_pairs": sum(count > 1 for count in pair_counts.values()),
        "recurring_multi_author_rosters": sum(count > 1 for count in roster_counts.values()),
        "coauthor_components": len(component_sizes),
        "largest_component": max(component_sizes, default=0),
        "single_name_components": component_sizes.count(1),
        "component_sizes": sorted(component_sizes, reverse=True),
        "author_rank": [
            {"name": name, "papers": count, "distinct_coauthors": len(neighbors[name])}
            for name, count in sorted(appearances.items(), key=lambda row: (-row[1], row[0].casefold(), row[0]))
        ],
        "coauthor_pair_rank": [
            {"authors": pair, "papers": count}
            for pair, count in sorted(pair_counts.items(), key=lambda row: (-row[1], str(row[0]).casefold(), str(row[0])))
        ],
        "multi_author_roster_rank": [
            {"authors": roster, "papers": count}
            for roster, count in sorted(roster_counts.items(), key=lambda row: (-row[1], str(row[0]).casefold(), str(row[0])))
        ],
    }


def affiliation_totals(papers):
    fields = {key: Counter() for key in ("name", "country", "region")}
    pairs = Counter()
    totals = Counter()
    for paper in papers:
        entries = paper["affiliations"]
        names = paper["authors"]
        author_places = paper["authorAffiliations"]
        independent = paper["authorIndependent"]
        if len(author_places) != len(names) or len(independent) != len(names):
            raise ValueError(f"Paper #{paper['id']}: author affiliation array is misaligned")
        institution_names = {item["name"] for item in entries}
        for places, flag in zip(author_places, independent):
            if not set(places) <= institution_names or len(places) != len(set(places)):
                raise ValueError(f"Paper #{paper['id']}: invalid author affiliation")
            if flag and places:
                raise ValueError(f"Paper #{paper['id']}: independent status conflicts with an institutional link")
        regions = {item["region"] for item in entries if item["region"]}
        pairs.update(combinations(sorted(regions), 2))
        for key in fields:
            fields[key].update({item[key] for item in entries if item[key]})
        totals.update({
            "papers_with_institutions": bool(entries),
            "papers_with_regions": bool(regions),
            "papers_with_multiple_regions": len(regions) > 1,
            "paper_institution_links": len(institution_names),
            "author_positions_with_institution": sum(bool(places) for places in author_places),
            "author_institution_links": sum(map(len, author_places)),
            "author_positions_explicitly_independent": sum(independent),
        })
    return dict(totals) | {
        "by_institution": fields["name"],
        "by_country_or_area": fields["country"],
        "by_region": fields["region"],
        "region_pairs": [{"regions": list(pair), "papers": count} for pair, count in sorted(pairs.items())],
    }


def paper_labels(papers):
    positive = [p for p in papers if p["status"] == "use"]
    topic_overlaps = Counter(pair for paper in papers for pair in combinations(sorted(set(paper["topics"])), 2))
    return {
        "primary_topics": Counter(p["primary"] for p in papers),
        "topic_tags": Counter(tag for p in papers for tag in set(p["topics"])),
        "topic_text_basis": Counter(p["basis"] for p in papers),
        "topic_overlaps": [{"topics": pair, "papers": count}
                           for pair, count in sorted(topic_overlaps.items(), key=lambda row: (-row[1], row[0]))],
        "ai": {
            "disclosure_status": Counter(p["status"] for p in papers),
            "disclosure_depth": Counter(p["depth"] for p in positive if p["depth"]),
            "purposes": Counter(x for p in positive for x in set(p["purpose"])),
            "tool_families": Counter(x for p in positive for x in set(p["tools"])),
            "models": Counter(x for p in positive for x in set(p["models"])),
            "generative_ai_as_research_subject": sum(p["subject"] for p in papers),
            "generative_ai_subject_with_disclosed_use": sum(p["subject"] for p in positive),
        },
        "formalization": {
            "papers_reporting_lean": sum(bool(p["lean"]) for p in papers),
            "papers_reporting_other_proof_assistants": sum(bool(p["formalization"]) for p in papers),
            "papers_with_verified_lean_source": sum(any(repo["status"] == "verified" for repo in p["leanRepos"]) for p in papers),
            "papers_reporting_separate_verification": Counter(p["verification"]["tool"] for p in papers if p["verification"]),
        },
    }


def comparison_totals(comparisons, by_id):
    result = []
    for comparison in comparisons:
        papers = comparison["papers"]
        if len({item.get("id") for item in papers}) != len(papers):
            raise ValueError(f"Missing or repeated paper in comparison {comparison['title']}")
        for item in papers:
            identifier = item["id"]
            paper = by_id[identifier]
            if not 1 <= item.get("method_page", 0) <= paper["pages"]:
                raise ValueError(f"Paper #{identifier}: invalid comparison method page")
            if item.get("status") != paper["status"]:
                raise ValueError(f"Paper #{identifier}: comparison and catalog disclosure differ")
        result.append({"title": comparison["title"], "papers": papers,
                       "paper_count": len(papers), "ai_statuses": Counter(item["status"] for item in papers)})
    return result


def main():
    site = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Recompute STOC 2027 report aggregates from its public catalog.")
    parser.add_argument("--report", type=Path, default=site / "stats.html")
    parser.add_argument("--manifest", type=Path, default=site / "assets" / "pdf-snapshot.json")
    parser.add_argument("--pdf-dir", type=Path, help="Verify byte counts and checksums for local PDFs named by paper ID.")
    args = parser.parse_args()
    report = ReportParser()
    report.feed(args.report.read_text(encoding="utf-8"))
    papers = json.loads(report.payloads["data"])
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    by_id = indexed(papers, "report catalog")
    if not report.comparisons:
        raise ValueError("No comparison tables found in the report")
    result = {
        "submissions": len(papers),
        "snapshot": verify_snapshot(by_id, manifest, args.pdf_dir),
        "pdf_length": paper_lengths(papers),
        "authorship": collaboration(papers),
        "affiliations": affiliation_totals(papers),
        **paper_labels(papers),
        "same_problem_comparisons": comparison_totals(report.comparisons, by_id),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
