import json
import sys
import uuid
from pathlib import Path
from app.chunker import chunk_pages
from app.loader import load_pdf
from app.store import add_chunk, search, store
from app.hybrid import hybrid_search
from app.rerank import rerank
from app.rag import extract_text, llm

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
import time


import json
import time

CACHE_PATH = BASE_DIR / "rewrites.json"


def rewrite_query(question):
    cache = json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else {}
    if question in cache:
        return cache[question]

    prompt = (
        "Rewrite this question as a short keyword search query for finding "
        "the answer in a document. Keep technical terms and names. "
        "Return only the query.\n\nQuestion: " + question
    )
    time.sleep(5)
    rewritten = extract_text(llm.invoke(prompt).content).strip()

    cache[question] = rewritten
    CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    return rewritten


def run_eval(pdf_path, questions_path, chunk_size, chunk_overlap, k, mode):
    thread_id = f"eval-{uuid.uuid4()}"
    try:
        pages = load_pdf(str(pdf_path))
        chunks = chunk_pages(pages, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        add_chunk(chunks, thread_id, Path(pdf_path).name)

        with open(questions_path, encoding="utf-8") as f:
            questions = json.load(f)

        hits = 0
        for q in questions:
            if mode == "rerank":
                docs = rerank(
                    q["question"], hybrid_search(thread_id, q["question"], k=20), k=k
                )
            elif mode == "hybrid":
                docs = hybrid_search(thread_id, q["question"], k=k)
            elif mode == "rewrite":
                docs = hybrid_search(thread_id, rewrite_query(q["question"]), k=k)
            else:
                docs = search(thread_id, q["question"], k=k)
            text = " ".join(d.page_content for d in docs).lower()
            hit = any(kw.lower() in text for kw in q["keywords"])
            hits += hit
            if not hit:
                print("MISS:", q["question"])

        rate = hits / len(questions)
        print(
            f"chunk_size={chunk_size} overlap={chunk_overlap} k={k} chunks={len(chunks)} hit_rate={rate:.0%}"
        )
    finally:
        # Clean up temporary evaluation vectors from ChromaDB
        store._collection.delete(where={"thread_id": str(thread_id)})


if __name__ == "__main__":
    chunk_size = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    chunk_overlap = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    k = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    mode = sys.argv[4] if len(sys.argv) > 4 else "vector"

    run_eval(
        PROJECT_ROOT / "data" / "2312.10997v5.pdf",
        BASE_DIR / "questions.json",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        k=k,
        mode=mode,
    )
