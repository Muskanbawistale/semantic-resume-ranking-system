from __future__ import annotations

from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.domain.models import CandidateResult, HiringRequirements


def build_pdf_report(requirements: HiringRequirements, results: list[CandidateResult]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm, topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    story = [Paragraph("Semantic Resume Ranking Report", styles["Title"]), Spacer(1, 8)]
    story.append(Paragraph(f"Role: {requirements.job_title or 'Not specified'}", styles["Heading2"]))
    story.append(Paragraph("Required skills: " + (", ".join(requirements.required_skills) or "Not specified"), styles["BodyText"]))
    story.append(Spacer(1, 12))
    table_data = [["Rank", "Candidate", "Final", "Conceptual Match", "Required skills"]]
    for result in results:
        table_data.append([result.rank, result.candidate_name, f"{result.score.final_score:.1f}", f"{result.score.conceptual_match_score:.1f}", f"{result.score.required_skill_coverage:.1f}"])
    table = Table(table_data, repeatRows=1, colWidths=[15*mm, 65*mm, 22*mm, 25*mm, 30*mm])
    table.setStyle(TableStyle([("GRID", (0,0), (-1,-1), 0.4, "#CBD5E1"), ("BACKGROUND", (0,0), (-1,0), "#E2E8F0"), ("VALIGN", (0,0), (-1,-1), "TOP")]))
    story.append(table)
    story.append(PageBreak())
    for result in results:
        story.extend([
            Paragraph(f"#{result.rank} {result.candidate_name} — {result.score.final_score:.1f}/100", styles["Heading1"]),
            Paragraph(result.summary, styles["BodyText"]), Spacer(1, 6),
            Paragraph("Strengths", styles["Heading3"]),
            Paragraph("<br/>".join(f"• {x}" for x in result.strengths) or "None identified", styles["BodyText"]),
            Paragraph("Improvement areas", styles["Heading3"]),
            Paragraph("<br/>".join(f"• {x}" for x in result.improvement_areas) or "None identified", styles["BodyText"]),
            Paragraph("Missing requirements", styles["Heading3"]),
            Paragraph(", ".join(result.missing_required_skills) or "None", styles["BodyText"]),
            Spacer(1, 12),
        ])
    doc.build(story)
    return buffer.getvalue()
