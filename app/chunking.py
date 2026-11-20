from loader import load_pdf
from chunk import chunk_pages

pages = load_pdf("data/AI_Similarity_Search_and_RAG_Concept_Map.pdf")
chunks = chunk_pages(pages, chunk_size=500, overlap=100)

print("Total chunks:", len(chunks))
print("--- Chunk 0 ---")
print(chunks[0]["text"])
print("--- Chunk 1 ---")
print(chunks[1]["text"])
print("Page of chunk 1:", chunks[1]["page"])
