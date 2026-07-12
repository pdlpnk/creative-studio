# Creative Brain v1 Search

Creative Brain v1 builds an in-memory local index of every Markdown Concept Card under `brain/concepts/`. It uses no OpenAI API, Claude, internet connection or third-party dependency.

## What is indexed

`index.py` reads YAML front matter from each `*.md` card and supplements it with supported `- Label: value` fields from parser-generated Markdown sections. This makes the current library searchable even though its older cards use slightly different front-matter shapes.

The unified `ConceptCard` object includes:

- source path, ID, YAML front matter and Markdown body;
- normalized GEO, funnel, language, headline, offer and CTA;
- visual colours, objects and composition where present;
- design-score values from the `Design Score` section;
- local promise text assembled from visible card fields for keyword search.

## Run the CLI

From the repository root:

```bash
python3 brain/search/index.py
```

The default command prints library statistics and one example of similar-creative search using the first indexed card.

Examples:

```bash
python3 brain/search/index.py --geo TR --funnel lead
python3 brain/search/index.py --cta "Detayları Gör"
python3 brain/search/index.py --objects smartphone --colors "light blue,white"
python3 brain/search/index.py --promises refund --min-design-score 7
python3 brain/search/index.py --similar CC-0003 --limit 5
```

## Search filters

| Filter | Searches |
|---|---|
| `--geo` | GEO from front matter. |
| `--funnel` | Funnel from front matter. |
| `--language` | Language from front matter. |
| `--cta` | CTA text. |
| `--headline` | Headline text. |
| `--objects` | Comma-separated object terms. |
| `--colors` | Comma-separated colour terms. |
| `--promises` | Offer, headline, hypothesis and local card body text. |
| `--min-design-score` | Average of available design scores for a card. |

All supplied filters are combined with AND. Matching is local, case-insensitive substring matching.

## Similar Creative

`similar_creatives` compares cards using Jaccard similarity across available:

- visual colours;
- visual objects;
- offer;
- CTA;
- composition tokens.

The score is a structural similarity signal, not a prediction of advertising performance.

## Statistics

The default report includes:

- total Concept Card count;
- TR/AZ distribution;
- registration/lead distribution;
- most frequent CTAs, colours and objects;
- average available design score;
- average available readability score.

Missing fields remain missing: the index does not invent metadata or infer real-world performance.
