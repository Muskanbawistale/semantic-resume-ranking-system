from __future__ import annotations

import re
from pathlib import Path

from src.domain.models import ParsedResume, ResumeSection, SectionName
from src.utils.text import clean_text, unique_preserve_order

SECTION_ALIASES: dict[str, SectionName] = {
    "summary": SectionName.summary, "profile": SectionName.summary,
    "professional summary": SectionName.summary, "objective": SectionName.summary,
    "skills": SectionName.skills, "technical skills": SectionName.skills,
    "core competencies": SectionName.skills, "technologies": SectionName.skills,
    "experience": SectionName.experience, "work experience": SectionName.experience,
    "professional experience": SectionName.experience, "employment": SectionName.experience,
    "projects": SectionName.projects, "academic projects": SectionName.projects,
    "personal projects": SectionName.projects,
    "education": SectionName.education, "academic background": SectionName.education,
    "certifications": SectionName.certifications, "certificates": SectionName.certifications,
}

COMMON_SKILLS = [
    "Python", "Java", "C++", "JavaScript", "TypeScript", "SQL", "PyTorch",
    "TensorFlow", "Keras", "Scikit-learn", "Pandas", "NumPy", "NLP",
    "Computer Vision", "Machine Learning", "Deep Learning", "LLM", "RAG",
    "Transformers", "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Git",
    "Linux", "FastAPI", "Flask", "Django", "Spark", "Kafka", "Airflow",
    "MLflow", "W&B", "FAISS", "PostgreSQL", "MongoDB", "Redis", "REST API",
]


class ResumeSectioner:
    heading_pattern = re.compile(r"^[A-Z][A-Z &/\-]{2,40}:?$")

    def parse(self, file_name: str, text: str) -> ParsedResume:
        sections = self._split_sections(text)
        candidate_name = self._candidate_name(file_name, text)
        skills = self._extract_known_skills(text)
        years = self._estimate_years(text)
        return ParsedResume(
            candidate_name=candidate_name,
            file_name=file_name,
            full_text=text,
            sections=sections,
            extracted_skills=skills,
            estimated_years_experience=years,
            education_text=self._section_text(sections, SectionName.education),
            certification_text=self._section_text(sections, SectionName.certifications),
        )

    def _split_sections(self, text: str) -> list[ResumeSection]:
        lines = [line.strip() for line in text.splitlines()]
        buckets: dict[SectionName, list[str]] = {name: [] for name in SectionName}
        current = SectionName.summary
        for line in lines:
            if not line:
                continue
            normalized = re.sub(r"[:\-]+$", "", line.lower()).strip()
            detected = SECTION_ALIASES.get(normalized)
            if detected is None and self.heading_pattern.match(line):
                detected = SECTION_ALIASES.get(normalized, SectionName.other)
            if detected is not None:
                current = detected
                continue
            buckets[current].append(line)

        sections = [
            ResumeSection(name=name, text=clean_text("\n".join(content)))
            for name, content in buckets.items() if content
        ]
        if not sections:
            sections = [ResumeSection(name=SectionName.other, text=text)]
        return sections

    @staticmethod
    def _candidate_name(file_name: str, text: str) -> str:
        first_lines = [line.strip() for line in text.splitlines() if line.strip()][:4]
        for line in first_lines:
            if 2 <= len(line.split()) <= 5 and not re.search(r"[@|\d]", line):
                return line.title()
        return Path(file_name).stem.replace("_", " ").replace("-", " ").title()

    @staticmethod
    def _extract_known_skills(text: str) -> list[str]:
        lowered = text.lower()
        return unique_preserve_order(
            skill for skill in COMMON_SKILLS if re.search(rf"(?<!\w){re.escape(skill.lower())}(?!\w)", lowered)
        )

    @staticmethod
    def _estimate_years(text: str) -> float:
        explicit = [float(v) for v in re.findall(r"(\d+(?:\.\d+)?)\+?\s+years?", text.lower())]
        return min(max(explicit, default=0.0), 40.0)

    @staticmethod
    def _section_text(sections: list[ResumeSection], name: SectionName) -> str:
        return "\n".join(section.text for section in sections if section.name == name)
