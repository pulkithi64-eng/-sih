"""Create one matching synthetic issuer fixture and one deliberately inconsistent PDF."""
from pathlib import Path
import shutil

import pymupdf
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf"
OUTPUT.mkdir(parents=True, exist_ok=True)
PREVIEW = ROOT / "tmp" / "pdfs"
PREVIEW.mkdir(parents=True, exist_ok=True)

correct = OUTPUT / "01_correct_demo_affiliation.pdf"
shutil.copy2(ROOT / "samples/piat/university_affiliation_2027-28.pdf", correct)

imaginary = OUTPUT / "02_imaginary_mismatch_affiliation.pdf"
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="Issuer", fontName="Helvetica-Bold", fontSize=20, leading=25, textColor=colors.HexColor("#0B2E59"), spaceAfter=8))
styles.add(ParagraphStyle(name="Warning", fontName="Helvetica-Bold", fontSize=10, leading=15, textColor=colors.HexColor("#9A3412"), spaceAfter=14))
styles["BodyText"].leading = 16
story = [
    Paragraph("Imaginary Meridian University", styles["Issuer"]),
    Paragraph("FICTIONAL TEST DATA - NOT AN OFFICIAL CERTIFICATE", styles["Warning"]),
    Paragraph("Office of the Registrar | Affiliation Section", styles["BodyText"]),
    Spacer(1, 7 * mm),
    Paragraph("Letter No.: STU/AFF/2026/2240", styles["BodyText"]),
    Paragraph("Date: 08/08/2026", styles["BodyText"]),
    Spacer(1, 9 * mm),
    Paragraph("CONTINUATION OF AFFILIATION", styles["Heading2"]),
    Paragraph("This deliberately inconsistent sample tests whether VeriSense compares submitted values with its simulated issuer record.", styles["BodyText"]),
    Spacer(1, 7 * mm),
]
rows = [
    ["Name of the Institution:", "Imaginary Horizon Institute of Technology"],
    ["University:", "Imaginary Meridian University"],
    ["Academic Year:", "2027-28"],
    ["Nature of Affiliation:", "Continuation (Permanent)"],
    ["Total Intake:", "9999"],
]
table = Table([[Paragraph(a, styles["BodyText"]), Paragraph(b, styles["BodyText"])] for a, b in rows], colWidths=[57 * mm, 105 * mm])
table.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2F6")),
    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
    ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
    ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ("TOPPADDING", (0, 0), (-1, -1), 10),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
]))
story.extend([
    table, Spacer(1, 9 * mm),
    Paragraph("Expected test behavior", styles["Heading2"]),
    Paragraph("The reference belongs to a different synthetic issuer record. Institution, university and intake values above are invented and should produce a mismatch. They must not be accepted as verified facts.", styles["BodyText"]),
    Spacer(1, 6 * mm),
    Paragraph("Synthetic specimen for local software testing only. No real person, institution or authority is represented.", styles["Warning"]),
])
SimpleDocTemplate(str(imaginary), pagesize=A4, rightMargin=24 * mm, leftMargin=24 * mm,
                  topMargin=22 * mm, bottomMargin=22 * mm,
                  title="VeriSense fictional affiliation mismatch test", author="VeriSense local test").build(story)

for pdf in (correct, imaginary):
    with pymupdf.open(pdf) as document:
        assert document.page_count == 1
        assert "STU/AFF/2026/2240" in document[0].get_text()
        document[0].get_pixmap(matrix=pymupdf.Matrix(1.2, 1.2)).save(PREVIEW / (pdf.stem + ".png"))
    print(pdf)
