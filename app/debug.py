import json
import sys
from pathlib import Path

from app.loader import load_pdf

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent


def check_keywords(search_word):
    pages = load_pdf(str(PROJECT_ROOT / "data" / "2312.10997v5.pdf"))
    full_text = " ".join(p["text"] for p in pages).lower()

    with open(BASE_DIR / "questions.json", encoding="utf-8") as f:
        questions = json.load(f)

    matched = False
    for q in questions:
        if search_word.lower() in q["question"].lower():
            matched = True
            print("\nQUESTION:", q["question"])
            for kw in q["keywords"]:
                print(" ", repr(kw), "found in PDF:", kw.lower() in full_text)

    if not matched:
        print(f"No question contains '{search_word}'.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python3 app/debug_miss.py "word from the question"')
        sys.exit(1)

    check_keywords(sys.argv[1])
