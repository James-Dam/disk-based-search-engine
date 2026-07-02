import argparse
import os
import time

from search_engine.core.search import MissingIndexError, raise_if_index_missing
from search_engine.service.search_service import search_query


def parse_args():
    parser = argparse.ArgumentParser(
        description="Search a generated disk-based inverted index."
    )
    parser.add_argument(
        "--index",
        default="index_output",
        help="Folder containing generated index files. Defaults to index_output.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Maximum number of results to print. Defaults to 10.",
    )
    return parser.parse_args()


def print_index_error(error):
    print(f"Missing or incomplete index folder: {error.index_folder}")
    print("Missing files:")
    for path in error.missing_files:
        print(f"  - {path}")
    print(f"Please run indexing first: python index.py --input ANALYST --output {error.index_folder}")


def main():
    args = parse_args()
    index_folder = os.path.normpath(args.index)

    try:
        raise_if_index_missing(index_folder)
    except MissingIndexError as error:
        print_index_error(error)
        raise SystemExit(1)

    while True:
        query = input("Enter query (or 'quit' to exit): ").strip()
        if query.lower() == "quit":
            break
        if not query:
            continue

        start_time = time.time()
        try:
            results = search_query(query, index_folder, top_k=args.top_k)
        except MissingIndexError as error:
            print_index_error(error)
            raise SystemExit(1)
        end_time = time.time()

        elapsed_ms = (end_time - start_time) * 1000
        print(f"Search took {elapsed_ms:.2f} ms.")

        if results:
            print(f"\nTop {len(results)} results for '{query}':")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result['url']}  (score: {result['score']:.4f})")
        else:
            print("No results found.")
        print()


if __name__ == "__main__":
    main()
