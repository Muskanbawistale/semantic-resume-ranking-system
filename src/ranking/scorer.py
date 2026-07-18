from __future__ import annotations

from collections import defaultdict

from src.domain.models import (
    CandidateResult, HiringRequirements, ParsedResume, ScoreBreakdown, SectionName,
)
from src.embeddings.encoder import EmbeddingEncoder
from src.ranking.matcher import lexical_overlap, partition_matches, term_present
from src.search.faiss_index import CosineFaissIndex
from src.utils.text import compact_excerpt

WEIGHTS = {
    "conceptual_match_score": 0.30,
    "required_skill_coverage": 0.25,
    "preferred_skill_coverage": 0.08,
    "experience_match": 0.12,
    "education_match": 0.07,
    "certification_match": 0.05,
    "project_relevance": 0.08,
    "lexical_overlap": 0.05,
}

SECTION_WEIGHTS = {
    SectionName.skills: 0.25,
    SectionName.experience: 0.35,
    SectionName.projects: 0.20,
    SectionName.education: 0.08,
    SectionName.certifications: 0.07,
    SectionName.summary: 0.05,
    SectionName.other: 0.05,
}


class ResumeRanker:
    def __init__(self, encoder: EmbeddingEncoder) -> None:
        self.encoder = encoder

    def rank(
        self, requirements: HiringRequirements, jd_text: str, resumes: list[ParsedResume]
    ) -> list[CandidateResult]:
        results = [self._score(requirements, jd_text, resume) for resume in resumes]
        results.sort(key=lambda result: result.score.final_score, reverse=True)
        for rank, result in enumerate(results, start=1):
            result.rank = rank
        return results

    def _score(
        self, req: HiringRequirements, jd_text: str, resume: ParsedResume
    ) -> CandidateResult:
        matched_req, missing_req = partition_matches(req.required_skills, resume.full_text)
        matched_pref, _ = partition_matches(req.preferred_skills, resume.full_text)
        matched_tools, _ = partition_matches(req.tools, resume.full_text)
        matched_certs, _ = partition_matches(req.certifications, resume.certification_text or resume.full_text)

        required_coverage = self._coverage(matched_req, req.required_skills)
        preferred_coverage = self._coverage(matched_pref, req.preferred_skills)
        experience_match = self._experience_score(resume.estimated_years_experience, req.experience.minimum_years)
        education_match = self._education_score(req, resume)
        certification_match = self._coverage(matched_certs, req.certifications)
        conceptual_match_score, section_scores = self._conceptual_match_score(
            req, jd_text, resume
        )
        project_relevance = section_scores.get(SectionName.projects, conceptual_match_score)
        lexical = lexical_overlap(
            [*req.required_skills, *req.tools, *req.domains], resume.full_text
        )

        components = {
            "conceptual_match_score": conceptual_match_score,
            "required_skill_coverage": required_coverage,
            "preferred_skill_coverage": preferred_coverage,
            "experience_match": experience_match,
            "education_match": education_match,
            "certification_match": certification_match,
            "project_relevance": project_relevance,
            "lexical_overlap": lexical,
        }
        final = 100 * sum(components[name] * WEIGHTS[name] for name in WEIGHTS)
        matching_projects = [
            compact_excerpt(section.text) for section in resume.sections
            if section.name == SectionName.projects and section_scores.get(SectionName.projects, 0) >= 0.45
        ][:3]

        strengths = self._strengths(components, matched_req, matched_tools)
        improvements = self._improvements(missing_req, components, req, resume)
        summary = self._summary(
            resume, matched_req, conceptual_match_score, experience_match
        )

        return CandidateResult(
            candidate_name=resume.candidate_name,
            file_name=resume.file_name,
            score=ScoreBreakdown(**{k: round(v * 100, 1) for k, v in components.items()}, final_score=round(final, 1)),
            matched_required_skills=matched_req,
            missing_required_skills=missing_req,
            matched_preferred_skills=matched_pref,
            matched_tools=matched_tools,
            matched_certifications=matched_certs,
            matching_projects=matching_projects,
            strengths=strengths,
            improvement_areas=improvements,
            summary=summary,
        )

    def _conceptual_match_score(
        self, req: HiringRequirements, jd_text: str, resume: ParsedResume
    ):
        requirement_text = self._requirement_text(req) or jd_text
        query = self.encoder.encode([requirement_text])[0]
        grouped: dict[SectionName, list[float]] = defaultdict(list)
        texts = [section.text for section in resume.sections]
        vectors = self.encoder.encode(texts)
        index = CosineFaissIndex(self.encoder.dimension)
        index.add(vectors.copy())
        hits = index.search(query.reshape(1, -1), top_k=len(texts))
        for hit in hits:
            section = resume.sections[hit.index]
            grouped[section.name].append(self._calibrate_cosine(hit.score))
        section_scores = {name: max(values) for name, values in grouped.items()}
        present_weight = sum(SECTION_WEIGHTS[name] for name in section_scores)
        conceptual_match_score = sum(
            section_scores[name] * SECTION_WEIGHTS[name] for name in section_scores
        ) / max(present_weight, 1e-9)
        return conceptual_match_score, section_scores

    @staticmethod
    def _calibrate_cosine(value: float) -> float:
        # General-purpose embedding cosine values cluster in a narrow range.
        # Map <=0.20 to 0 and >=0.80 to 1 for an interpretable component score.
        return min(1.0, max(0.0, (value - 0.20) / 0.60))

    @staticmethod
    def _coverage(matched: list[str], expected: list[str]) -> float:
        return 1.0 if not expected else len(matched) / len(expected)

    @staticmethod
    def _experience_score(actual: float, required: float) -> float:
        if required <= 0:
            return 1.0
        return min(actual / required, 1.0)

    @staticmethod
    def _education_score(req: HiringRequirements, resume: ParsedResume) -> float:
        if not req.education.minimum_level and not req.education.fields:
            return 1.0
        text = resume.education_text or resume.full_text
        level = 1.0 if not req.education.minimum_level or term_present(req.education.minimum_level, text) else 0.0
        fields = 1.0 if not req.education.fields else sum(term_present(f, text) for f in req.education.fields) / len(req.education.fields)
        return 0.6 * level + 0.4 * fields

    @staticmethod
    def _requirement_text(req: HiringRequirements) -> str:
        return "\n".join([
            f"Role: {req.job_title}",
            "Required skills: " + ", ".join(req.required_skills),
            "Preferred skills: " + ", ".join(req.preferred_skills),
            "Tools: " + ", ".join(req.tools),
            "Responsibilities: " + "; ".join(req.responsibilities),
            "Domains: " + ", ".join(req.domains),
            "Experience areas: " + ", ".join(req.experience.relevant_areas),
        ]).strip()

    @staticmethod
    def _strengths(components: dict[str, float], skills: list[str], tools: list[str]) -> list[str]:
        strengths = []
        if components["conceptual_match_score"] >= 0.70:
            strengths.append("Strong overall conceptual match with the role")
        if components["required_skill_coverage"] >= 0.75:
            strengths.append("Covers most required skills")
        if components["experience_match"] >= 1.0:
            strengths.append("Meets the stated experience threshold")
        if tools:
            strengths.append("Relevant tools: " + ", ".join(tools[:5]))
        if skills:
            strengths.append("Key skill matches: " + ", ".join(skills[:5]))
        return strengths[:4]

    @staticmethod
    def _improvements(missing: list[str], components: dict[str, float], req: HiringRequirements, resume: ParsedResume) -> list[str]:
        items = []
        if missing:
            items.append("Missing or not evidenced: " + ", ".join(missing[:6]))
        if components["experience_match"] < 1 and req.experience.minimum_years:
            items.append(f"Resume shows {resume.estimated_years_experience:g} explicit years versus {req.experience.minimum_years:g} required")
        if components["project_relevance"] < 0.45:
            items.append("Projects do not strongly demonstrate the target responsibilities")
        if components["education_match"] < 0.6:
            items.append("Education requirement is not clearly evidenced")
        return items[:4]

    @staticmethod
    def _summary(
        resume: ParsedResume, matched: list[str], conceptual_match_score: float, exp: float
    ) -> str:
        alignment = (
            "strong"
            if conceptual_match_score >= 0.7
            else "moderate"
            if conceptual_match_score >= 0.45
            else "limited"
        )
        experience = "meets" if exp >= 1 else "partially meets"
        skills = ", ".join(matched[:4]) or "few explicit required skills"
        return (
            f"{resume.candidate_name} has a {alignment} conceptual match, {experience} the "
            f"experience requirement, and demonstrates {skills}."
        )
