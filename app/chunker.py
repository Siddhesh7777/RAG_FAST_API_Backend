from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_pages(pages, chunk_size=1000, chunk_overlap=200):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    chunks = []
    for page in pages:
        for piece in splitter.split_text(page["text"]):
            chunks.append({"text": piece, "page": page["page"]})
    return chunks
