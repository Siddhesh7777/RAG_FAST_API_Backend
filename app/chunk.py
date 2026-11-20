def chunk_text(text, chunk_size, overlap):
    start = 0
    step = chunk_size - overlap
    chunks = []
    while start < len(text):
        if start + chunk_size > len(text):
            chunk = text[start:]
        chunk = text[start : start + chunk_size]
        chunks.append(chunk)
        start += step
    return chunks


def chunk_pages(pages, chunk_size, overlap):
    chunked_pages = []
    for page in pages:
        text = page["text"]
        pieces = chunk_text(text, chunk_size, overlap)
        for i, piece in enumerate(pieces):
            chunked_pages.append(
                {
                    "page_number": page["page_number"],
                    "chunk_number": i + 1,
                    "text": piece,
                }
            )
    return chunked_pages
