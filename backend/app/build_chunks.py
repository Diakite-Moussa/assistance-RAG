"""Usage (depuis backend/) : uv run python -m app.build_chunks --strategy structural"""
import argparse
import json

from .chunking import chunk_corpus
from .config import settings
from .extract import extract_corpus


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default=settings.chunk_strategy, choices=["fixed", "structural"])
    ap.add_argument("--size", type=int, default=settings.chunk_size)
    ap.add_argument("--overlap", type=int, default=settings.chunk_overlap)
    ap.add_argument("--max-chars", type=int, default=settings.max_section_chars)
    args = ap.parse_args()

    docs = extract_corpus(settings.corpus_dir)
    chunks = chunk_corpus(docs, args.strategy, args.size, args.overlap, args.max_chars)
    out = settings.output_dir / f"chunks_{args.strategy}.json"
    out.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(docs)} documents -> {len(chunks)} fragments ({args.strategy}) -> {out}")


if __name__ == "__main__":
    main()