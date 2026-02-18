from fpdf import FPDF


def _latin1(text: str) -> str:
    """Encode to latin-1, replacing unsupported chars — fpdf built-in fonts are latin-1 only."""
    return text.encode("latin-1", errors="replace").decode("latin-1")


def generate_capture_pdf(
    title: str,
    organisation: str | None,
    url: str | None,
    text_snapshot: str | None,
    captured_at: str,
    deadline: str | None = None,
) -> bytes:
    """Generate a PDF archive of a job posting from its text snapshot."""
    pdf = FPDF()
    pdf.set_margins(20, 20, 20)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.multi_cell(0, 10, _latin1(title or "Job Posting"), align="L")
    pdf.ln(2)

    # Metadata
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(80, 80, 80)

    if organisation:
        pdf.cell(0, 7, _latin1(f"Organisation: {organisation}"), ln=True)
    if url:
        display_url = url if len(url) <= 90 else url[:87] + "..."
        pdf.cell(0, 7, _latin1(f"URL: {display_url}"), ln=True)
    pdf.cell(0, 7, _latin1(f"Captured: {captured_at}"), ln=True)
    if deadline:
        pdf.set_text_color(180, 60, 0)
        pdf.cell(0, 7, _latin1(f"Deadline: {deadline}"), ln=True)
        pdf.set_text_color(80, 80, 80)

    # Divider
    pdf.ln(3)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(5)

    # Body text
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)

    body = text_snapshot or "No text content was extracted from this page."
    pdf.multi_cell(0, 5, _latin1(body[:50000]))

    return bytes(pdf.output())
