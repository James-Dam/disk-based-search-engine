# Disk-Based Search Engine

A disk-backed search engine for a crawled web corpus. The project builds an inverted index from JSON documents, stores the index on disk, and exposes both a terminal search interface and a FastAPI backend.

This began as a university course project and is now being evolved into a polished search application suitable for portfolio and recruiter review. The current architecture separates core indexing/search logic from CLI and HTTP interfaces.

## Quick Start

The repository includes `analyst.zip`, a smaller dataset intended for fast local setup. The full `DEV/` dataset is optional, too large for GitHub, and not included.

Step 1: unzip analyst.zip -> produces ANALYST/

```powershell
Expand-Archive analyst.zip -DestinationPath .
```

On macOS or Linux:

```bash
unzip analyst.zip
```

Step 2: install dependencies

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

On macOS or Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Step 3: run indexing using ANALYST/

```bash
python index.py --input ANALYST --output index_output
```

Step 4: run terminal search

```bash
python search.py --index index_output
```

Step 5: run the API server

```bash
uvicorn api.main:app --reload
```

## Current Architecture

```text
.
|-- index.py                         # CLI wrapper for indexing
|-- search.py                        # CLI wrapper for terminal search
|-- api/
|   |-- __init__.py
|   `-- main.py                      # Uvicorn entry point shim
|-- search_engine/
|   |-- __init__.py
|   |-- core/
|   |   |-- __init__.py
|   |   |-- index.py                 # Core indexing logic
|   |   `-- search.py                # Core lookup and ranking logic
|   |-- service/
|   |   |-- __init__.py
|   |   `-- search_service.py        # Reusable service wrapper
|   `-- api/
|       |-- __init__.py
|       `-- main.py                  # FastAPI application
|-- requirements.txt
|-- analyst.zip                      # Included default dataset archive
|-- ANALYST/                         # Extracted default dataset, ignored by git
|-- index_output/                    # Generated index files, ignored by git
`-- DEV/                             # Optional full dataset, not included
```

Separation of concerns:

- CLI: user interaction and command-line arguments only.
- Core: indexing, disk lookup, and ranking logic.
- Service: reusable function boundary for CLI and API callers.
- API: HTTP interface built with FastAPI.

## CLI Usage

The default indexer command is:

```bash
python index.py
```

This is equivalent to:

```bash
python index.py --input ANALYST --output index_output
```

If `ANALYST/` is missing, the indexer prints:

```text
Missing dataset. Please unzip analyst.zip to create ANALYST/
```

Run terminal search:

```bash
python search.py --index index_output
```

Optional result count:

```bash
python search.py --index index_output --top-k 10
```

Example terminal queries:

```text
machine learning
computer science
informatics
graduate admissions
artificial intelligence
database systems
```

## API Usage

Start the backend:

```bash
uvicorn api.main:app --reload
```

The API uses `index_output` by default. To point it at a different generated index folder, set `SEARCH_INDEX_PATH` before starting Uvicorn.

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Response:

```json
{"status":"ok"}
```

Search request:

```bash
curl "http://127.0.0.1:8000/search?q=machine%20learning&top_k=10"
```

Example response:

```json
[
  {
    "url": "https://example.edu/page",
    "score": 12.3456,
    "title": "",
    "snippet": ""
  }
]
```

If the generated index is missing or incomplete, the API returns HTTP 503 with details telling you to run indexing first.

## Reusable Search Function

The service layer exposes:

```python
from search_engine.service.search_service import search_query

results = search_query("machine learning", index_path="index_output", top_k=10)
```

Return format:

```python
[
    {
        "url": "https://example.edu/page",
        "score": 12.3456,
        "title": "",
        "snippet": "",
    }
]
```

`title` and `snippet` are currently empty placeholders so the API shape is ready for future result enrichment without changing the search ranking or disk index format.

## How Indexing Works

`search_engine.core.index` walks the input directory recursively and processes JSON files. For each page, it removes URL fragments, skips duplicate URLs, extracts visible HTML text, and separately extracts important text from tags such as `title`, `h1`, `h2`, `h3`, `b`, and `strong`.

The indexer tokenizes alphanumeric terms, lowercases them, applies Porter stemming, and stores postings in the format:

```text
[doc_id, term_frequency, important_term_frequency]
```

To keep memory usage manageable, the indexer periodically writes sorted partial index files to disk. After the corpus is processed, it performs a k-way merge into `final_index.txt`. The final index stores one postings list per line, while `term_offsets.json` maps each term to its byte offset in the final index for direct lookup during search.

## How Searching Works

`search_engine.core.search` loads `term_offsets.json` and `doc_map.json`, then opens `final_index.txt` on demand. Query terms are tokenized and stemmed the same way as indexed terms.

For a query, the search logic:

1. Looks up each query term's postings list using the byte offset map.
2. Retrieves documents that contain all query terms.
3. Falls back to documents that contain any query term if no strict AND match exists.
4. Scores candidates with TF-IDF style ranking.
5. Boosts terms found in important HTML tags.
6. Applies URL-based adjustments for noisy pages and query terms in URLs.
7. Returns structured results for CLI or API presentation.

## Current Limitations

- The default dataset is the smaller `ANALYST/` corpus from `analyst.zip`.
- The optional full `DEV/` dataset is not included because it is too large for GitHub.
- Index files must already exist before running search.
- `title` and `snippet` are placeholders.
- There is no automated test suite yet.
- There is no React frontend yet.
- There is no Docker setup yet.
- Ranking is intentionally simple and explainable rather than production-grade.
- Generated index files can be large and are treated as local build artifacts.

## Planned Improvements

- Add a React frontend for query entry and result display.
- Add Docker support for repeatable local setup.
- Add tests for tokenization, indexing, offset lookup, API responses, and ranking behavior.
- Add safer recovery for interrupted indexing runs.
- Add real result titles and snippets.

## Repository Status

This step introduces a FastAPI backend and service layer while preserving the indexing algorithm, TF-IDF logic, disk-based index format, and ranking system.
