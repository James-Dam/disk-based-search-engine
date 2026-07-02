from nltk.stem import PorterStemmer
import json
import math
import os
import re


INDEX_FOLDER = "index_output"
INDEX_PATH = os.path.join(INDEX_FOLDER, "final_index.txt")
OFFSETS_PATH = os.path.join(INDEX_FOLDER, "term_offsets.json")
DOC_MAP_PATH = os.path.join(INDEX_FOLDER, "doc_map.json")

TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


class MissingIndexError(FileNotFoundError):
    def __init__(self, index_folder, missing_files):
        self.index_folder = index_folder
        self.missing_files = missing_files
        message = f"Missing or incomplete index folder: {index_folder}"
        super().__init__(message)


def get_index_paths(index_folder):
    return {
        "index": os.path.join(index_folder, "final_index.txt"),
        "offsets": os.path.join(index_folder, "term_offsets.json"),
        "doc_map": os.path.join(index_folder, "doc_map.json"),
    }


def get_missing_index_files(index_folder):
    paths = get_index_paths(index_folder)

    if not os.path.isdir(index_folder):
        return list(paths.values())

    return [path for path in paths.values() if not os.path.isfile(path)]


def validate_index_folder(index_folder):
    return not get_missing_index_files(index_folder)


def raise_if_index_missing(index_folder):
    missing_files = get_missing_index_files(index_folder)
    if missing_files:
        raise MissingIndexError(index_folder, missing_files)


def load_index(index_folder=INDEX_FOLDER):
    """
    Loads the term offsets and doc map from disk into memory.
    Returns:
        tuple: (term_offsets dict, doc_map dict)
    """
    paths = get_index_paths(index_folder)

    with open(paths["offsets"], "r", encoding="utf-8") as f:
        term_offsets = json.load(f)

    with open(paths["doc_map"], "r", encoding="utf-8") as f:
        doc_map = json.load(f)

    return term_offsets, doc_map


def tokenize_query(query, stemmer):
    """
    Tokenizes and stems a query string
    Args:
        query: raw query string from user
        stemmer: Porter Stemmer
    Returns:
        list: stemmed query tokens
    """
    tokens = TOKEN_RE.findall(query.lower())
    return [stemmer.stem(t) for t in tokens]


def get_postings(term, term_offsets, index_file):
    """
    Gets the postings list for one term without loading the full index.
    Args:
        term: stemmed query term
        term_offsets: mapping from term to byte offset
        index_file: opened final_index.txt file
    Returns:
        list: postings for the term, or None if not found
    """
    if term not in term_offsets:
        return None

    offset = term_offsets[term]
    index_file.seek(offset)

    line = index_file.readline()

    if not line:
        return None

    postings = json.loads(line.strip())

    return postings


def normalize_url(url):
    """
    Normalizes URLs so near-duplicate URLs are treated as the same.
    """
    url = url.lower().strip()
    url = url.rstrip("/")

    if url.endswith("/index.php"):
        url = url[:-10]

    if url.endswith("/index"):
        url = url[:-6]

    return url


def get_url_score_multiplier(url):
    """
    Gives lower scores to noisy/list/archive pages.
    This is general, not query-specific.
    """
    url = url.lower()
    multiplier = 1.0

    # Similar to the black list filtering from the web crawler
    # Specifically wanted these to get lower ratings
    bad_patterns = [
        "/tag/",
        "/category/",
        "/page/",
        "/community/news/",
        "view_news",
        "view_article",
        "mailman/listinfo",
        "notes_",
        "wordlist",
        ".txt"
    ]

    for pattern in bad_patterns:
        if pattern in url:
            multiplier *= 0.5

    return multiplier


def get_url_query_boost(url, raw_query_terms):
    """
    Gives a small boost when query terms appear in the URL.
    Helps pages whose URL directly matches the user's intent.
    """
    url = url.lower()
    url = url.replace("-", " ")
    url = url.replace("_", " ")

    boost = 0

    for term in raw_query_terms:
        if term in url:
            boost += 2

    return boost


def get_and_candidates(query_terms, term_postings):
    """
    Finds documents that contain every query term.
    Args:
        query_terms: stemmed query terms
        term_postings: postings for query terms
    Returns:
        set: doc ids that contain every query term
    """
    for term in query_terms:
        if term not in term_postings:
            return set()

    # AND: find doc_ids that appear in ALL terms' postings
    # start with smaller sets first
    sets = [set(posting[0] for posting in term_postings[t]) for t in query_terms]
    sets.sort(key=len)

    common_doc_ids = sets[0]
    for s in sets[1:]:
        common_doc_ids = common_doc_ids & s

    return common_doc_ids


def get_or_candidates(term_postings):
    """
    Finds documents that contain at least one query term.
    Used when strict AND retrieval finds no results.
    """
    doc_ids = set()

    for term in term_postings:
        for posting in term_postings[term]:
            doc_ids.add(posting[0])

    return doc_ids


def get_matched_term_counts(doc_ids, term_postings):
    """
    Counts how many query terms each document matched.
    Used to help OR fallback ranking.
    """
    matched_counts = {}

    for doc_id in doc_ids:
        matched_counts[doc_id] = 0

    for term in term_postings:
        for posting in term_postings[term]:
            doc_id = posting[0]

            if doc_id in doc_ids:
                matched_counts[doc_id] += 1

    return matched_counts


def search(query, term_offsets, doc_map, top_n=5, index_path=INDEX_PATH):
    """
    Search the index for a query using AND logic and tf-idf ranking.
    Args:
        query: raw query string
        term_offsets: mapping from term to byte offset
        doc_map: mapping of doc_id to url/path
        top_n: number of top results to return
    Returns:
        list of (url, score) tuples sorted by score descending
    """
    stemmer = PorterStemmer()
    query_terms = tokenize_query(query, stemmer)
    raw_query_terms = TOKEN_RE.findall(query.lower())

    if not query_terms:
        return []

    N = len(doc_map)  # total number of documents

    # get postings for each query term
    # postings format: [doc_id, tf, important_tf]
    term_postings = {}

    with open(index_path, "r", encoding="utf-8") as index_file:
        for term in query_terms:
            postings = get_postings(term, term_offsets, index_file)

            if postings is not None:
                term_postings[term] = postings

    if not term_postings:
        return []

    # AND: find doc_ids that appear in ALL terms' postings
    # start with doc_ids from the first term, intersect with the rest
    common_doc_ids = get_and_candidates(query_terms, term_postings)

    use_or_fallback = False

    # if strict AND returns no results, use OR
    if not common_doc_ids:
        use_or_fallback = True
        common_doc_ids = get_or_candidates(term_postings)

    if not common_doc_ids:
        return []

    # score each candidate document using tf-idf
    # tf-idf = tf * log(N / df)
    # important words get a 2x boost
    scores = {}
    for term in term_postings:
        postings = term_postings[term]
        df = len(postings)  # doc frequency
        idf = math.log(N / df) if df > 0 else 0

        for posting in postings:
            doc_id = posting[0]
            if doc_id not in common_doc_ids:
                continue

            tf = posting[1]
            important_tf = posting[2]

            # base tf-idf score
            tf_idf = (1 + math.log(tf)) * idf if tf > 0 else 0

            # boost for important words (title, headings, bold)
            importance_boost = (1 + math.log(important_tf)) * idf * 2 if important_tf > 0 else 0

            scores[doc_id] = scores.get(doc_id, 0) + tf_idf + importance_boost

    matched_counts = get_matched_term_counts(common_doc_ids, term_postings)

    # apply URL-based score adjustments
    adjusted_scores = {}

    for doc_id in scores:
        doc_info = doc_map.get(str(doc_id)) or doc_map.get(doc_id)

        if doc_info:
            url = doc_info["url"]

            multiplier = get_url_score_multiplier(url)
            boost = get_url_query_boost(url, raw_query_terms)

            # OR fallback needs an extra reward for matching more query terms
            # so a page matching 3 terms ranks above a page matching only 1.
            if use_or_fallback:
                coverage_boost = matched_counts.get(doc_id, 0) * 5
            else:
                coverage_boost = 0

            adjusted_scores[doc_id] = (scores[doc_id] * multiplier) + boost + coverage_boost

    # sort by score descending and return top N URLs
    ranked = sorted(adjusted_scores.items(), key=lambda x: x[1], reverse=True)

    results = []
    seen_urls = set()

    for doc_id, score in ranked:
        doc_info = doc_map.get(str(doc_id)) or doc_map.get(doc_id)
        if doc_info:
            url = doc_info["url"]
            normalized = normalize_url(url)

            if normalized in seen_urls:
                continue

            seen_urls.add(normalized)
            results.append((url, score))

            if len(results) == top_n:
                break

    return results


def search_query(query: str, index_path: str, top_k: int = 10):
    """
    Search a generated index folder and return structured results.

    Args:
        query: Raw query string.
        index_path: Folder containing final_index.txt, term_offsets.json, and doc_map.json.
        top_k: Maximum number of results to return.
    """
    index_folder = os.path.normpath(index_path)
    raise_if_index_missing(index_folder)

    paths = get_index_paths(index_folder)
    term_offsets, doc_map = load_index(index_folder)
    ranked_results = search(
        query,
        term_offsets,
        doc_map,
        top_n=top_k,
        index_path=paths["index"],
    )

    return [
        {
            "url": url,
            "score": float(score),
            "title": "",
            "snippet": "",
        }
        for url, score in ranked_results
    ]
