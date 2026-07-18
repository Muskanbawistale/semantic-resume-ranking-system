from src.document_processing.sectioner import ResumeSectioner
from src.domain.models import SectionName


def test_sections_and_name_are_detected():
    text = "Jane Doe\nSUMMARY\nML engineer\nSKILLS\nPython, PyTorch\nEXPERIENCE\n3 years building models"
    resume = ResumeSectioner().parse("jane.pdf", text)
    assert resume.candidate_name == "Jane Doe"
    assert any(s.name == SectionName.skills for s in resume.sections)
    assert resume.estimated_years_experience == 3
