from pypdf import PdfReader


def load_pdf(file_path):
    reader = PdfReader(file_path)
    pages = []
    for pagenumber, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        pages.append({"page": pagenumber, "text": text})
    return pages
