from __future__ import annotations

from src.document_processing.extractor import DocumentExtractor
from src.document_processing.sectioner import ResumeSectioner
from src.embeddings.encoder import EmbeddingEncoder
from src.llm.groq_requirements import GroqRequirementExtractor
from src.ranking.scorer import ResumeRanker


class RankingService:
    def __init__(self, encoder: EmbeddingEncoder, groq_api_key: str | None = None) -> None:
        self.document_extractor = DocumentExtractor()
        self.sectioner = ResumeSectioner()
        self.requirement_extractor = GroqRequirementExtractor(api_key=groq_api_key)
        self.ranker = ResumeRanker(encoder)

    def analyze(self, jd_file: tuple[str, bytes], resume_files: list[tuple[str, bytes]]):
        jd = self.document_extractor.extract(*jd_file)
        requirements = self.requirement_extractor.extract(jd.text)
        resumes = []
        warnings = []
        for name, data in resume_files:
            try:
                extracted = self.document_extractor.extract(name, data)
                resumes.append(self.sectioner.parse(name, extracted.text))
                if extracted.warning:
                    warnings.append(f"{name}: {extracted.warning}")
            except Exception as exc:
                warnings.append(f"{name}: {exc}")
        if not resumes:
            raise ValueError("No valid resumes could be processed.")
        return requirements, self.ranker.rank(requirements, jd.text, resumes), warnings
