# How the data was produced

## Snapshot and catalog

The report includes the [current public submission index](https://sigact-stoc.github.io/stoc2027/) and retains #1003 from the [original index](https://stoc2027.sigact-ec.workers.dev/). The current index added #90 and no longer lists #1003. Both count in the report. The [report](../stats.html) embeds one record per paper. The [snapshot manifest](../assets/pdf-snapshot.json) records official PDF URLs where available, snapshot URLs, and the page counts, byte counts, and SHA-256 checksums of the captured files. Page-length statistics count the entire submitted PDF. Evidence links use physical PDF page numbers.

## From papers to fields

| Field | How it was produced |
| --- | --- |
| Authors and collaboration | Author names and order come from the index. Counts use the displayed name after Unicode and spacing normalization. Each unordered coauthor pair counts once per paper. Repeated teams match complete author sets. |
| Affiliations | Institutional names and author links come from explicit bylines and address blocks. Names were normalized, and locations were assigned from the paper or an institutional registry. Each institution or location counts at most once per paper. Cross-region papers have affiliations in at least two identified regions. |
| Topics | Rules match field-specific terms in titles and available abstracts or opening text. A paper can receive a primary topic and secondary tags. Weak evidence can leave a paper unclassified. |
| AI disclosures | Rules screen extracted PDF text for author statements. The catalog records disclosure status, reported purposes, named tools or models, and strongest reported role. A missing or unclear statement leaves use uncertain. Research about generative AI is tracked separately from AI use in producing the paper. |
| Formalization | Lean and Rocq counts use author reports, including partial formalizations. A verified public source is accessible and linked to the paper. Independent verification and SAT or SMT checks are recorded separately. |
| Paper highlights | Examples summarize claims reported in the manuscripts and link to evidence pages. The report does not assess proof correctness. |

The overview percentages use all indexed papers. Group comparisons use the denominator stated in each chart. AI disclosure shares by group use papers with readable text.

## Reproduce the data

From the directory containing `stats.html`, use Python 3.9 or later.

```sh
python3 source/recompute.py
```

This reads the embedded catalog and manifest and recomputes the main counts and rankings. To check a local PDF collection, pass a directory containing files named by paper ID.

```sh
python3 source/recompute.py --pdf-dir pdfs
```

Use Poppler’s `pdftotext -layout` to prepare an ID-named text file for each PDF. The following commands take that text directory as input.

```sh
python3 source/classify_topics.py --text-dir text > topics.json
python3 source/classify_ai.py --text-dir text > ai-screening.json
```

The screening commands derive candidate topic and disclosure labels from text. To reproduce the published counts, use the report catalog, which contains the recorded labels, affiliation assignments, and proof-source fields.

## Report assets

The HTML contains the chart and interface code. To rebuild the math asset with a local KaTeX 0.19.1 distribution, run:

```sh
node source/math/build-math.cjs path/to/katex.js assets/math.js stats.html
```
