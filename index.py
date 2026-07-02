import argparse
import os

from search_engine.core.index import index, write_index_and_report


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build a disk-based inverted index from a local JSON corpus."
    )
    parser.add_argument(
        "--input",
        default="ANALYST",
        help="Input corpus folder containing JSON documents. Defaults to ANALYST.",
    )
    parser.add_argument(
        "--output",
        default="index_output",
        help="Output folder for generated index files. Defaults to index_output.",
    )
    return parser.parse_args()


def validate_input_folder(input_folder):
    if os.path.isdir(input_folder):
        return True

    default_input = os.path.normcase(os.path.normpath("ANALYST"))
    requested_input = os.path.normcase(os.path.normpath(input_folder))
    if requested_input == default_input:
        print("Missing dataset. Please unzip analyst.zip to create ANALYST/")
    else:
        print(f"Missing dataset folder: {input_folder}")
    return False


def main():
    args = parse_args()
    input_folder = os.path.normpath(args.input)
    output_folder = os.path.normpath(args.output)

    if not validate_input_folder(input_folder):
        raise SystemExit(1)

    doc_map, final_index_path, offsets_path = index(input_folder, output_folder)
    write_index_and_report(doc_map, final_index_path, offsets_path, output_folder)


if __name__ == "__main__":
    main()
