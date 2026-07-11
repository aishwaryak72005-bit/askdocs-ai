import re
import pdfplumber


def extract_text_from_pdf(file_obj):
    """
    Extracts text from every page of a PDF using pdfplumber.
    Returns (full_text, page_count).
    file_obj must be a file-like object opened in binary mode.
    """
    text_chunks = []
    with pdfplumber.open(file_obj) as pdf:
        page_count = len(pdf.pages)
        for i, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            text_chunks.append(f"\n--- Page {i} ---\n{page_text}")
    return "".join(text_chunks).strip(), page_count


_PAGE_MARKER = re.compile(r"(?:^|\n)--- Page (\d+) ---\n")


def chunk_text(full_text, chunk_size=900, overlap=150):
    """
    Splits text produced by extract_text_from_pdf() into overlapping chunks,
    tagging each chunk with the page number it came from (so answers can
    cite sources). Chunking happens within a page's text, not across pages.

    Returns a list of {"text": str, "page": int} dicts.
    """
    parts = _PAGE_MARKER.split(full_text)
    # re.split with a capturing group returns: [pre, page_num, page_text, page_num, page_text, ...]
    chunks = []
    for i in range(1, len(parts), 2):
        page_num = int(parts[i])
        page_text = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if not page_text:
            continue

        start = 0
        while start < len(page_text):
            end = start + chunk_size
            piece = page_text[start:end].strip()
            if piece:
                chunks.append({"text": piece, "page": page_num})
            if end >= len(page_text):
                break
            start = end - overlap

    return chunks
