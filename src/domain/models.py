from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SectionName(str, Enum):
    summary = "summary"
    skills = "skills"
    experience = "experience"
    projects = "projects"
    education = "education"
    certifications = "certifications"
    other = "other"


class ExperienceRequirement(BaseModel):
    minimum_years: float = Field(default=0, ge=0, le=60)
    preferred_years: float | None = Field(default=None, ge=0, le=60)
    relevant_areas: list[str] = Field(default_factory=list)


class EducationRequirement(BaseModel):
    minimum_level: str | None = None
    fields: list[str] = Field(default_factory=list)


class HiringRequirements(BaseModel):
    job_title: str = ""
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    experience: ExperienceRequirement = Field(default_factory=ExperienceRequirement)
    education: EducationRequirement = Field(default_factory=EducationRequirement)
    certifications: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)

    @field_validator(
        "required_skills", "preferred_skills", "tools", "certifications",
        "responsibilities", "domains", "nice_to_have", mode="before"
    )
    @classmethod
    def normalize_lists(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return [str(item).strip() for item in value if str(item).strip()]


class ResumeSection(BaseModel):
    name: SectionName
    text: str


class ParsedResume(BaseModel):
    candidate_name: str
    file_name: str
    full_text: str
    sections: list[ResumeSection]
    extracted_skills: list[str] = Field(default_factory=list)
    estimated_years_experience: float = 0
    education_text: str = ""
    certification_text: str = ""


class ScoreBreakdown(BaseModel):
    conceptual_match_score: float
    required_skill_coverage: float
    preferred_skill_coverage: float
    experience_match: float
    education_match: float
    certification_match: float
    project_relevance: float
    lexical_overlap: float
    final_score: float


class CandidateResult(BaseModel):
    rank: int = 0
    candidate_name: str
    file_name: str
    score: ScoreBreakdown
    matched_required_skills: list[str] = Field(default_factory=list)
    missing_required_skills: list[str] = Field(default_factory=list)
    matched_preferred_skills: list[str] = Field(default_factory=list)
    matched_tools: list[str] = Field(default_factory=list)
    matched_certifications: list[str] = Field(default_factory=list)
    matching_projects: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    improvement_areas: list[str] = Field(default_factory=list)
    summary: str = ""
