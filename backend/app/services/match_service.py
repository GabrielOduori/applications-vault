"""
Keyword-overlap CV-to-job match scoring.
Fully offline — no external API required.
"""
import re
from pathlib import Path

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "up", "about", "into", "through", "is",
    "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "shall", "can", "not", "we", "you", "your", "our", "their", "they",
    "it", "its", "this", "that", "these", "those", "as", "if", "so",
    "than", "then", "when", "where", "how", "what", "which", "who",
    "all", "more", "most", "other", "some", "such", "no", "nor", "too",
    "very", "just", "also", "both", "each", "few", "many", "either",
    "must", "need", "will", "able", "per", "etc", "inc", "ltd", "plc",
    "role", "job", "work", "team", "join", "help", "make", "use", "new",
    "get", "see", "day", "good", "great", "able", "key", "including",
}


def tokenize(text: str) -> set[str]:
    """Extract meaningful keyword tokens from text."""
    # Match alphanumeric tokens including tech tokens like C++, .NET, C#
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}", text.lower())
    return {w for w in words if w not in STOPWORDS}


def extract_text_from_file(file_path: Path, mime_type: str | None) -> str:
    """Extract readable text from a stored document file."""
    # Try plain UTF-8 first (works for .txt, plain CV exports, some .rtf)
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        # Reject if it looks like binary garbage (low printable ratio)
        printable = sum(1 for c in text if c.isprintable() or c.isspace())
        if len(text) > 0 and printable / len(text) > 0.85:
            return text
    except Exception:
        pass

    # Try PDF extraction
    is_pdf = (
        mime_type in ("application/pdf", "application/x-pdf")
        or file_path.suffix.lower() == ".pdf"
    )
    if is_pdf:
        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages)
        except Exception:
            pass

    return ""


def compute_match(job_text: str, doc_text: str) -> dict:
    """
    Compare document text against job description text.
    Returns score (0-100), matched keywords, and missing keywords.
    """
    job_keywords = tokenize(job_text)
    doc_keywords = tokenize(doc_text)

    if not job_keywords:
        return {
            "score": 0.0,
            "matched": [],
            "missing": [],
            "job_keyword_count": 0,
            "doc_keyword_count": len(doc_keywords),
        }

    matched = sorted(job_keywords & doc_keywords)
    missing = sorted(job_keywords - doc_keywords)
    score = round(len(matched) / len(job_keywords) * 100, 1)

    return {
        "score": score,
        "matched": matched[:60],
        "missing": missing[:40],
        "job_keyword_count": len(job_keywords),
        "doc_keyword_count": len(doc_keywords),
    }
