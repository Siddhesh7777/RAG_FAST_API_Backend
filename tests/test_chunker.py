from app.chunker import chunk_pages


def test_chunks_keep_page_numbers():
    pages = [{"page": 3, "text": "hello world. " * 200}]
    chunks = chunk_pages(pages, chunk_size=300, chunk_overlap=50)
    assert len(chunks) > 1
    assert all(c["page"] == 3 for c in chunks)


def test_chunks_respect_size():
    pages = [{"page": 1, "text": "word " * 1000}]
    chunks = chunk_pages(pages, chunk_size=300, chunk_overlap=50)
    assert all(len(c["text"]) <= 300 for c in chunks)


def test_empty_page_gives_no_chunks():
    assert chunk_pages([{"page": 1, "text": ""}]) == []
