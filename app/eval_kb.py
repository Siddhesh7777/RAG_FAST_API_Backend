import argparse
import json
from pathlib import Path

from app.hybrid import hybrid_search_where, keyword_ranking, semantic_ranking
from app.store import company_filter, search_where

EMPLOYEE = ["all"]
HR = ["all", "hr_only"]


def _has(docs, keywords):
    text = " ".join(" ".join(d.page_content for d in docs).split()).lower()
    return any(k.lower() in text for k in keywords)


def run_eval(mode, path, k):
    where = company_filter(EMPLOYEE)
    questions = json.loads(Path(path).read_text(encoding="utf-8"))
    hits = 0
    for q in questions:
        if mode == "hybrid":
            docs = hybrid_search_where(where, q["question"], k=k)
        else:
            docs = search_where(where, q["question"], k=k)
        if _has(docs, q["keywords"]):
            hits += 1
        else:
            print("MISS:", q["question"])
    print(
        f"knowledge base | mode={mode} k={k} hit_rate={hits / len(questions):.0%} ({hits}/{len(questions)})"
    )


def check_access(path, k):
    questions = json.loads(Path(path).read_text(encoding="utf-8"))
    leaked_any = False
    for q in questions:
        for name, fn in [("vector", semantic_ranking), ("keyword", keyword_ranking)]:
            employee_docs = fn(company_filter(EMPLOYEE), q["question"], k)
            hr_docs = fn(company_filter(HR), q["question"], k)
            leaked = _has(employee_docs, q["keywords"])
            reachable = _has(hr_docs, q["keywords"])
            leaked_any = leaked_any or leaked
            print(
                f"{'LEAK' if leaked else 'ok  '} | {name:7s} | HR can reach: {reachable} | {q['question']}"
            )
    print("ACCESS CHECK:", "FAILED" if leaked_any else "PASSED")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["vector", "hybrid", "access"])
    parser.add_argument("questions", help="path to a questions JSON file")
    parser.add_argument("--k", type=int, default=4)
    args = parser.parse_args()
    if args.mode == "access":
        check_access(args.questions, args.k)
    else:
        run_eval(args.mode, args.questions, args.k)


if __name__ == "__main__":
    main()
