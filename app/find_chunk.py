import sys
import uuid
from pathlib import Path

from app.chunker import chunk_pages
from app.hybrid import hybrid_search
from app.loader import load_pdf
from app.store import add_chunk, store

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def find(question, keyword, chunk_size=1000, overlap=200):
    thread_id = f"find-{uuid.uuid4()}"
    try:
        pages = load_pdf(str(PROJECT_ROOT / "data" / "2312.10997v5.pdf"))
        chunks = chunk_pages(pages, chunk_size=chunk_size, chunk_overlap=overlap)
        add_chunk(chunks, thread_id, "paper.pdf")

        total = len(chunks)
        docs = hybrid_search(thread_id, question, k=total, pool=total)

        kw = keyword.lower()
        found = False
        for rank, d in enumerate(docs, start=1):
            text = " ".join(d.page_content.split())
            if kw in text.lower():
                found = True
                pos = text.lower().index(kw)
                print(f"\nrank {rank} of {total}, page {d.metadata.get('page')}")
                print("...", text[max(0, pos - 150) : pos + 250], "...")
        if not found:
            print("Keyword is not inside any single chunk.")
    finally:
        store.delete(where={"thread_id": thread_id})


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Usage: python3 app/find_chunk.py "question" "keyword"')
        sys.exit(1)
    find(sys.argv[1], sys.argv[2])
