import argparse
import hashlib
import json
from pathlib import Path

from langchain_core.documents import Document

from app.chunker import chunk_pages
from app.config import settings
from app.loader import load_pdf
from app.store import store


def fingerprint(pdf_path, entry):
    h = hashlib.sha256()
    h.update(Path(pdf_path).read_bytes())
    h.update(json.dumps(entry, sort_keys=True).encode())
    h.update(f"{settings.chunk_size}:{settings.chunk_overlap}".encode())
    return h.hexdigest()


def existing_fingerprint(doc_id):
    data = store.get(where={"doc_id": doc_id}, include=["metadatas"])
    metas = data["metadatas"]
    return metas[0].get("fingerprint") if metas else None


def ingest_one(folder, entry, force=False):
    path = folder / entry["file"]
    fp = fingerprint(path, entry)
    old = existing_fingerprint(entry["doc_id"])

    if old == fp and not force:
        return "unchanged"
    if old is not None:
        store.delete(where={"doc_id": entry["doc_id"]})

    pages = load_pdf(str(path))
    chunks = chunk_pages(
        pages, chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
    )
    if not chunks:
        raise ValueError(f"No text found in {entry['file']} (scanned PDF?)")

    docs = [
        Document(
            page_content=c["text"],
            metadata={
                "scope": "company",
                "doc_id": entry["doc_id"],
                "filename": entry["file"],
                "title": entry["title"],
                "department": entry["department"],
                "visibility": entry["visibility"],
                "version": entry["version"],
                "effective_date": entry["effective_date"],
                "page": c["page"],
                "fingerprint": fp,
            },
        )
        for c in chunks
    ]
    store.add_documents(docs)
    return "replaced" if old is not None else "added"


def prune(manifest_ids):
    data = store.get(where={"scope": "company"}, include=["metadatas"])
    stale = {m["doc_id"] for m in data["metadatas"]} - manifest_ids
    for doc_id in stale:
        store.delete(where={"doc_id": doc_id})
    return sorted(stale)


def main():
    parser = argparse.ArgumentParser(
        description="Load company documents into the knowledge base"
    )
    parser.add_argument("folder", nargs="?", default="knowledge")
    parser.add_argument("--force", action="store_true", help="re-ingest everything")
    parser.add_argument(
        "--prune",
        action="store_true",
        help="remove documents no longer in the manifest",
    )
    args = parser.parse_args()

    folder = Path(args.folder)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))

    counts = {}
    for entry in manifest:
        try:
            status = ingest_one(folder, entry, args.force)
        except Exception as e:
            status = "FAILED"
            print(f"FAILED     {entry['doc_id']:12s} {entry['file']}: {e}")
        else:
            print(f"{status:10s} {entry['doc_id']:12s} {entry['file']}")
        counts[status] = counts.get(status, 0) + 1

    if args.prune:
        removed = prune({e["doc_id"] for e in manifest})
        for doc_id in removed:
            print(f"removed    {doc_id}")
            counts["removed"] = counts.get("removed", 0) + 1

    print("summary:", counts)


if __name__ == "__main__":
    main()
# Run `python ingest.py` for a normal sync—it reads `knowledge/manifest.json`,
# ingests new or edited PDFs, skips unchanged ones using SHA-256 fingerprints, and
# logs any missing files without crashing. Add `--prune` (`python ingest.py --prune`)
# to also delete old company chunks from ChromaDB that were removed from the manifest, or a
# dd `--force` (`python ingest.py --force`) to ignore fingerprints and re-ingest every docu
# ment from scratch (optionally passing a custom folder name before the flags).
