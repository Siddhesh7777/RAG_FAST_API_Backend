import sys
import uuid
from pathlib import Path

from chunker import chunk_pages
from hybrid import hybrid_search
from loader import load_pdf
from store import add_chunk, store

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def inspect(question, keyword, k=20):
    thread_id = f"inspect-{uuid.uuid4()}"
    try:
        pages = load_pdf(str(PROJECT_ROOT / "data" / "2312.10997v5.pdf"))
        chunks = chunk_pages(pages, chunk_size=1000, chunk_overlap=200)

        add_chunk(chunks, thread_id, "paper.pdf")
        docs = hybrid_search(thread_id, question, k=k)
        for rank, d in enumerate(docs, start=1):
            text = " ".join(d.page_content.split()).lower()
            flag = "HAS KEYWORD" if keyword.lower() in text else "-"
            print(rank, "page", d.metadata.get("page"), flag)
    finally:
        store.delete(where={"thread_id": thread_id})


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Usage: python3 app/inspect_miss.py "question" "keyword"')
        sys.exit(1)
    inspect(sys.argv[1], sys.argv[2])
