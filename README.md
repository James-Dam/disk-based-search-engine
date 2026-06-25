# Disk-Based Search Engine

A disk-backed search engine for a crawled web corpus. The project builds an inverted index from JSON documents, stores the index on disk, and provides a terminal search interface that ranks matching URLs with TF-IDF style scoring.

This began as a university course project and is now being evolved into a polished search application suitable for portfolio and recruiter review. The current repository intentionally keeps the original terminal workflow while improving documentation, setup, and project structure.

## Why This Project Exists

The goal is to demonstrate the core systems work behind a search engine without relying on a database or hosted search service. The indexer processes a large local corpus, writes compact searchable files to disk, and the search program retrieves postings by byte offset instead of loading the entire index into memory.

## Features

- Disk-based inverted index built from local JSON documents.
- HTML text extraction with Beautiful Soup.
- Tokenization and Porter stemming for normalized term matching.
- Duplicate URL filtering during indexing.
- Partial index flushing to limit memory usage on large corpora.
- K-way merge into a final index file.
- Byte-offset lookup table for fast term retrieval at search time.
- Terminal search with AND matching and OR fallback.
- TF-IDF style scoring with boosts for title, heading, bold, and URL matches.
- Simple index analytics report with document count, token count, and index size.

## Current Architecture

```text
.
|-- index.py              # Builds the disk-based inverted index from ./DEV
|-- search.py             # Runs the interactive terminal search program
|-- requirements.txt      # Minimal Python runtime dependencies
|-- README.md             # Project documentation
|-- DEV/                  # Expected extracted input corpus, ignored by git
|-- index_output/         # Generated index files, ignored by git
|-- developer.zip         # Course dataset archive, if present
`-- analyst.zip           # Course dataset archive, if present
```

The current scripts assume this local layout:

- Input corpus: `DEV/`
- Generated index folder: `index_output/`
- Final index file: `index_output/final_index.txt`
- Term offset map: `index_output/term_offsets.json`
- Document map: `index_output/doc_map.json`
- Index report: `index_output/report.txt`

Each input document is expected to be a JSON file with at least:

- `url`: the source URL for the page
- `content`: the raw HTML content for the page

## How Indexing Works

`index.py` walks the `DEV/` directory recursively and processes JSON files. For each page, it removes URL fragments, skips duplicate URLs, extracts visible HTML text, and separately extracts important text from tags such as `title`, `h1`, `h2`, `h3`, `b`, and `strong`.

The indexer tokenizes alphanumeric terms, lowercases them, applies Porter stemming, and stores postings in the format:

```text
[doc_id, term_frequency, important_term_frequency]
```

To keep memory usage manageable, the indexer periodically writes sorted partial index files to disk. After the corpus is processed, it performs a k-way merge into `final_index.txt`. The final index stores one postings list per line, while `term_offsets.json` maps each term to its byte offset in the final index for direct lookup during search.

## How Searching Works

`search.py` loads `term_offsets.json` and `doc_map.json`, then opens `final_index.txt` on demand. Query terms are tokenized and stemmed the same way as indexed terms.

For a query, the search program:

1. Looks up each query term's postings list using the byte offset map.
2. Retrieves documents that contain all query terms.
3. Falls back to documents that contain any query term if no strict AND match exists.
4. Scores candidates with TF-IDF style ranking.
5. Boosts terms found in important HTML tags.
6. Applies URL-based adjustments for noisy pages and query terms in URLs.
7. Prints the top results with scores and search latency.

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

The current runtime dependencies are intentionally small: Beautiful Soup for HTML parsing and NLTK for Porter stemming.

## Prepare the Corpus

The indexer currently expects an extracted `DEV/` directory at the repository root. If you only have the course dataset archive, extract it so the final path looks like:

```text
disk-based-search-engine/
`-- DEV/
    |-- aiclub_ics_uci_edu/
    |-- archive_ics_uci_edu/
    `-- ...
```

## Run the Indexer

From the repository root:

```bash
python index.py
```

This reads from `./DEV` and writes generated files into `index_output/`. On the current corpus, the generated report shows tens of thousands of indexed documents and over one million unique normalized tokens.

Re-run the indexer whenever the `DEV/` corpus changes or when `index_output/` has been deleted.

## Run Terminal Search

After `index_output/` exists:

```bash
python search.py
```

Then enter queries at the prompt. Type `quit` to exit.

Example queries:

```text
machine learning
computer science
informatics
graduate admissions
artificial intelligence
database systems
```

## Current Limitations

- The input path is hardcoded to `./DEV` in `index.py`.
- The search program is terminal-only.
- Index files must already exist before running `search.py`.
- There is no automated test suite yet.
- There is no API layer or web interface yet.
- Ranking is intentionally simple and explainable rather than production-grade.
- Generated index files can be large and are treated as local build artifacts.

## Planned Improvements

- Add a FastAPI backend around the existing search functionality.
- Add a React frontend for query entry and result display.
- Add Docker support for repeatable local setup.
- Add tests for tokenization, indexing, offset lookup, and ranking behavior.
- Make input and output paths configurable.
- Add safer error handling for missing corpus or missing index files.

## Repository Status

This step focuses on presentation and setup only. The existing indexing and search behavior is preserved so the current terminal workflow remains the baseline for future improvements.
