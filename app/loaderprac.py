import sys
from loader import load_pdf

pages = load_pdf("data/AI_Similarity_Search_and_RAG_Concept_Map.pdf")
print("Number of pages:", len(pages))
print("Characters on page 1:", len(pages[0]["text"]))
print(pages[0]["text"][:500])
