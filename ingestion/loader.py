"""
loader.py
---------
Reads a document from disk and extracts its raw text.

The job of the loader is narrow and important: take ONE file (PDF, Word, or
plain text) and return a list of "records". Each record is one logical unit of
the document (a PDF page, or a whole Word file) plus the metadata we need later
to cite it: the source filename and the page number.

We keep page numbers because the whole point of PlantBrain is trustworthy,
*citable* answers — "see page 7 of the pump manual", not "the AI said so".
"""

from pathlib import Path

# PyMuPDF is imported as `fitz`. On some newer builds the module is `pymupdf`,
# so we fall back gracefully and the rest of the code never has to care.
try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    import pymupdf as fitz

from docx import Document  # python-docx, for .docx files


def _load_pdf(path: str) -> list[dict]:
    """Extract text from a PDF, one record per page (so we keep page numbers)."""
    records = []
    doc = fitz.open(path)
    for page_number, page in enumerate(doc, start=1):
        text = page.get_text("text")
        if text.strip():  # skip blank/image-only pages
            records.append(
                {"text": text, "source": Path(path).name, "page": page_number}
            )
    doc.close()
    return records


def _load_docx(path: str) -> list[dict]:
    """Extract text from a Word document. Word has no real 'pages', so page=None."""
    doc = Document(path)
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    if not text.strip():
        return []
    return [{"text": text, "source": Path(path).name, "page": None}]


def _load_txt(path: str) -> list[dict]:
    """Extract text from a plain .txt file."""
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    if not text.strip():
        return []
    return [{"text": text, "source": Path(path).name, "page": None}]


# Map each file extension to the function that knows how to read it.
# Adding a new format later = add one function and one line here.
LOADERS = {".pdf": _load_pdf, ".docx": _load_docx, ".txt": _load_txt}


def load_document(path: str) -> list[dict]:
    """
    Public entry point. Picks the right loader based on the file extension.

    Returns a list of records: [{"text": str, "source": str, "page": int|None}, ...]
    Raises ValueError on unsupported file types so the UI can show a clear message.
    """
    ext = Path(path).suffix.lower()
    if ext not in LOADERS:
        supported = ", ".join(LOADERS)
        raise ValueError(f"Unsupported file type '{ext}'. Supported: {supported}")
    return LOADERS[ext](path)