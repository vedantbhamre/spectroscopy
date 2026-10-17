"""Ingestion: materials folder → processed_data/pages.json + chunks.json → embeddings → Qdrant.

    python -m app.ingestion.processor --materials ~/Downloads/materials [--wipe] [--no-index]

Source IDs come from the file name prefix (S01_…pdf → S01). The method comparison
table (xlsx) is the machine-readable S01 Table 1, cited as "S01 Table 1 (p.6)".
S02 is mostly slide images, so the team's transcriptions in data/visual_notes.json
are added as kind "visual_note" pages; the UI labels citations to them.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from app.config import BACKEND_DIR, settings
from app.ingestion.chunking import chunk_pages
from app.ingestion.loaders import load

VISUAL_NOTES = BACKEND_DIR / "data" / "visual_notes.json"
SOURCE_RE = re.compile(r"^(S0[1-6])_")
# Organizer documents that are not citable sources: scenarios and worked answers stay out of retrieval.
EXCLUDE = {"AFS_Examples_and_Reference.docx", "customer_scenarios_for_final_evaluation.txt"}


def collect_pages(materials: Path) -> list[dict]:
    pages: list[dict] = []
    for path in sorted(materials.iterdir()):
        if not path.is_file() or path.name in EXCLUDE or path.name.startswith("."):
            continue
        if path.suffix.lower() == ".xlsx" and "method_comparison" in path.name:
            for _, text in load(path):
                pages.append({"source": "S01", "page": 6, "kind": "table", "label": "Table 1 (p.6)", "file": path.name, "text": text})
            continue
        m = SOURCE_RE.match(path.name)
        if not m:
            print(f"skip (no S0n prefix): {path.name}")
            continue
        try:
            for page, text in load(path):
                if text.strip():
                    pages.append({"source": m.group(1), "page": page, "kind": "extracted", "file": path.name, "text": text})
        except ValueError as e:
            print(f"skip: {e}")
    if VISUAL_NOTES.exists():
        pages.extend(json.loads(VISUAL_NOTES.read_text()))
    return pages


def index(chunks: list[dict], wipe: bool) -> int:
    from app.services.embedding import embed_texts, embeddings_available
    from app.services.vectorstore import recreate_collection, upsert_chunks

    if not embeddings_available():
        print("No GEMINI_API_KEY: skipping vector indexing (retrieval falls back to BM25).")
        return 0
    recreate_collection(wipe=wipe)
    vectors = embed_texts([c["text"] for c in chunks])
    return upsert_chunks(chunks, vectors)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--materials", type=Path, default=settings.MATERIALS_DIR)
    ap.add_argument("--wipe", action="store_true", help="drop and recreate the Qdrant collection")
    ap.add_argument("--no-index", action="store_true", help="only write processed_data/, skip embeddings")
    args = ap.parse_args(argv)

    materials = args.materials.expanduser()
    if not materials.is_dir():
        sys.exit(f"Materials folder not found: {materials}")

    pages = collect_pages(materials)
    chunks = chunk_pages(pages)
    settings.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    settings.PAGES_FILE.write_text(json.dumps(pages, ensure_ascii=False, indent=1))
    settings.CHUNKS_FILE.write_text(json.dumps(chunks, ensure_ascii=False, indent=1))
    by_source: dict[str, int] = {}
    for p in pages:
        by_source[p["source"]] = by_source.get(p["source"], 0) + 1
    print(f"pages: {len(pages)} {by_source} · chunks: {len(chunks)} → {settings.PROCESSED_DIR}")

    if not args.no_index:
        n = index(chunks, args.wipe)
        if n:
            print(f"indexed {n} chunks into Qdrant collection '{settings.QDRANT_COLLECTION}'")


if __name__ == "__main__":
    main()
