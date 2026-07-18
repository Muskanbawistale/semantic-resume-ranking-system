from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.settings import settings
from src.embeddings.encoder import EmbeddingEncoder
from src.reporting.pdf_report import build_pdf_report
from src.service import RankingService

st.set_page_config(page_title="Semantic Resume Ranker", page_icon="🧠", layout="wide")


@st.cache_resource(show_spinner="Loading semantic embedding model...")
def load_encoder(model_name: str) -> EmbeddingEncoder:
    return EmbeddingEncoder(model_name)


def badge_list(items: list[str], empty: str = "None") -> str:
    return " · ".join(items) if items else empty


st.title("Semantic Resume Ranking System")
st.caption("Section-aware, explainable ranking. Groq extracts JD requirements; deterministic code ranks candidates.")

with st.sidebar:
    st.header("Configuration")
    if settings.groq_api_key:
        st.success("Groq API configured")
    else:
        st.error("Groq API is not configured")
    st.text_input("Embedding model", value=settings.embedding_model, disabled=True)
    st.caption("Files are processed in memory and are not persisted by this application.")

left, right = st.columns(2)
with left:
    jd_upload = st.file_uploader("1. Upload job description", type=["pdf", "docx", "txt"], accept_multiple_files=False)
with right:
    resume_uploads = st.file_uploader("2. Upload resumes", type=["pdf", "docx"], accept_multiple_files=True)

analyze = st.button("Analyze and rank", type="primary", use_container_width=True)

if analyze:
    if not jd_upload:
        st.error("Upload one job description.")
        st.stop()
    if not resume_uploads:
        st.error("Upload at least one resume.")
        st.stop()
    if not settings.groq_api_key:
        st.error("Configure GROQ_API_KEY in the .env file and restart the application.")
        st.stop()

    try:
        with st.spinner("Extracting documents, structuring requirements, and scoring candidates..."):
            encoder = load_encoder(settings.embedding_model)
            service = RankingService(encoder=encoder)
            requirements, results, warnings = service.analyze(
                (jd_upload.name, jd_upload.getvalue()),
                [(f.name, f.getvalue()) for f in resume_uploads],
            )
            st.session_state["analysis"] = (requirements, results, warnings)
    except Exception as exc:
        st.error(str(exc))

if "analysis" in st.session_state:
    requirements, results, warnings = st.session_state["analysis"]
    if warnings:
        with st.expander(f"Processing warnings ({len(warnings)})"):
            for warning in warnings:
                st.warning(warning)

    with st.expander("Extracted hiring requirements", expanded=False):
        st.json(requirements.model_dump())

    st.subheader("Ranked candidates")
    df = pd.DataFrame([{
        "Rank": r.rank, "Candidate": r.candidate_name, "Final score": r.score.final_score,
        "Conceptual Match": r.score.conceptual_match_score,
        "Required skills": r.score.required_skill_coverage,
        "Experience": r.score.experience_match, "Projects": r.score.project_relevance,
    } for r in results])
    st.dataframe(df, hide_index=True, use_container_width=True)

    for result in results:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"### #{result.rank} {result.candidate_name}")
                st.write(result.summary)
            with c2:
                st.metric("Final score", f"{result.score.final_score:.1f}/100")
            tabs = st.tabs(["Evidence", "Score breakdown", "Projects"])
            with tabs[0]:
                a, b = st.columns(2)
                with a:
                    st.markdown("**Matched required skills**")
                    st.success(badge_list(result.matched_required_skills))
                    st.markdown("**Matched tools**")
                    st.info(badge_list(result.matched_tools))
                    st.markdown("**Strengths**")
                    for item in result.strengths:
                        st.write("✓", item)
                with b:
                    st.markdown("**Missing required skills**")
                    st.warning(badge_list(result.missing_required_skills))
                    st.markdown("**Matched certifications**")
                    st.info(badge_list(result.matched_certifications))
                    st.markdown("**Improvement areas**")
                    for item in result.improvement_areas:
                        st.write("•", item)
            with tabs[1]:
                st.caption(
                    "Conceptual Match measures how closely the meaning and context of the "
                    "resume align with the job description."
                )
                st.bar_chart(pd.DataFrame({"Score": {
                    "Conceptual Match": result.score.conceptual_match_score,
                    "Required skills": result.score.required_skill_coverage,
                    "Preferred skills": result.score.preferred_skill_coverage,
                    "Experience": result.score.experience_match,
                    "Education": result.score.education_match,
                    "Certifications": result.score.certification_match,
                    "Projects": result.score.project_relevance,
                    "Lexical": result.score.lexical_overlap,
                }}))
            with tabs[2]:
                if result.matching_projects:
                    for project in result.matching_projects:
                        st.write("•", project)
                else:
                    st.write("No strongly matching project section was detected.")

    report = build_pdf_report(requirements, results)
    st.download_button("Download ranking report", data=report, file_name="resume_ranking_report.pdf", mime="application/pdf")
