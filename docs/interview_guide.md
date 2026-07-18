# Technical Interview Guide

This guide summarizes the system's implemented behavior, design trade-offs, and responsible claims for portfolio discussions.

## 60-Second Explanation

The project ranks resumes against a job description while keeping the decision path inspectable. Groq converts the job description into a validated requirements schema, but it never receives resumes or assigns candidate scores. Resumes are parsed into sections and embedded locally with Sentence Transformers. A per-resume FAISS index measures contextual alignment, while deterministic functions calculate skill, experience, education, certification, and lexical evidence. Those components are combined with fixed weights into a Final Score, and the Streamlit interface exposes the evidence behind each rank.

## End-to-End Walkthrough

1. The user uploads one job description and multiple resumes.
2. PDF, DOCX, or TXT content is extracted and validated.
3. Groq returns strict JSON describing the hiring requirements; Pydantic validates its structure.
4. Resume headings are mapped to summary, skills, experience, projects, education, certifications, or other.
5. Structured requirements and each resume section are embedded with `all-mpnet-base-v2` by default.
6. Exact cosine search produces calibrated section scores and Conceptual Match.
7. Boundary-aware matching and scoring helpers calculate the remaining evidence signals.
8. Candidates are sorted by Final Score and shown with explanations and a PDF report.

## Key Facts

| Topic | Implemented behavior |
|---|---|
| LLM role | Job-requirement extraction only |
| Resume data sent to Groq | None |
| Conceptual Match | Section-aware, calibrated cosine alignment |
| Final Score | Fixed weighted combination of eight components |
| Vector search | Exact `IndexFlatIP`, rebuilt for each resume's sections |
| Default embedding model | `sentence-transformers/all-mpnet-base-v2` |
| Experience estimation | Largest explicit `N years` statement, capped at 40 |
| Document persistence | None at application level |
| OCR | Not implemented |

## Conceptual Match vs. Final Score

**Conceptual Match** answers: *How closely do the meaning and context of this resume align with the structured role requirements?* It is calculated from section embeddings and contributes 30% of the result.

**Final Score** answers: *How strong is the candidate across every implemented semantic and explicit evidence signal?* It is the value used for ranking.

```text
Final Score = 30% Conceptual Match
            + 25% required skill coverage
            + 12% experience match
            +  8% preferred skill coverage
            +  8% project relevance
            +  7% education match
            +  5% certification match
            +  5% lexical overlap
```

The weights are transparent defaults. They have not been validated on recruiter-labeled outcomes.

## Architecture Questions

### Why not let the LLM rank candidates?

LLM-generated rankings are difficult to reproduce, calibrate, unit test, and audit. This project uses the model for a narrower task where schema validation is possible. Pydantic validates structure and constraints, not whether every extracted requirement is factually correct. The model still influences downstream results through those requirements, so it is an upstream dependency rather than a neutral component.

### What does “deterministic ranking” mean here?

Given the same validated requirements, extracted text, embeddings, and configuration, the score calculation and ordering rules are fixed and inspectable. The complete workflow is not guaranteed to be bit-for-bit reproducible because Groq is an external model and model availability can change.

### Why embed resume sections instead of the whole document?

A single long embedding can dilute relevant experience and may obscure where evidence came from. Section embeddings preserve categories such as experience, skills, and projects and support relative section weighting. The cost is more embedding operations per resume.

### Why use cosine similarity?

The encoder returns L2-normalized vectors. Their inner product therefore equals cosine similarity, which measures directional alignment independent of vector magnitude. Raw cosine scores are calibrated before they are exposed as Conceptual Match.

### Why use FAISS for such a small index?

Each resume gets a small, temporary `IndexFlatIP` containing its detected section vectors. NumPy would also be sufficient at this size, but FAISS makes the retrieval boundary and cosine-search intent explicit. Approximate indexing would only be justified after a corpus-scale redesign and measurement.

### Why use `all-mpnet-base-v2`?

It is a quality-oriented general-purpose default that remains practical for local inference in this project. It is slower and larger than MiniLM alternatives, and the repository does not claim that it is optimal without a labeled benchmark.

## Scoring and Matching Questions

### How is Conceptual Match calculated?

The query contains the role, required and preferred skills, tools, responsibilities, domains, and relevant experience areas. FAISS compares it with every detected resume section. Cosines are calibrated with `clamp((cosine - 0.20) / 0.60, 0, 1)`, then combined using relative section coefficients normalized over the categories present.

### What happens when a resume section is missing?

Conceptual Match renormalizes its relative coefficients over detected sections, so a missing category does not automatically collapse the semantic score. Project relevance uses the projects-section score when available and otherwise falls back to overall Conceptual Match.

### What happens when the job description omits a requirement?

An empty required, preferred, or certification list receives a component value of `1.0`. No minimum experience and no education requirement also receive `1.0`. These values are constant across candidates for the same job description, so they do not alter relative ordering, although they can increase absolute scores.

### How are short or punctuated skills matched safely?

The matcher uses escaped regular expressions with explicit alphanumeric boundaries instead of normalized substring checks. Aliases cover cases such as R/RStudio, C++/CPP, C#/C Sharp, .NET/dotnet/ASP.NET, Node.js/NodeJS, and React.js/ReactJS/React. Plain C also rejects `+` and `#` suffixes so it does not claim C++ or C#.

### Why retain a lexical component when embeddings already capture meaning?

Semantic alignment and exact textual evidence solve different problems. The 5% lexical signal provides a small check across required skills, tools, and domains without overpowering contextual similarity.

## Explainability Questions

### What can a reviewer inspect?

The interface shows validated requirements, candidate rank, Final Score, Conceptual Match, matched and missing required skills, tools, certifications, strengths, improvement areas, component scores, and qualifying project excerpts. The PDF report provides a portable summary of rankings and candidate evidence.

### Are the explanations generated by an LLM?

No. Candidate summaries, strengths, and improvement areas are produced by fixed templates, thresholds, and matched evidence. This keeps explanations aligned with the scoring inputs, although it does not make them a complete causal or fairness analysis.

## Privacy and Responsible AI

### Which data leaves the application environment?

Only job-description text is submitted to Groq. Resume text is parsed, embedded, and scored within the application process. Uploaded documents are not explicitly persisted by the application, but production deployment would still require platform-level retention and privacy review.

### How does the project address bias?

Implemented controls are limited: the LLM does not receive resumes or directly rank candidates, score components are visible, and the documentation requires human review. The code does **not** redact names or protected attributes, calculate fairness metrics, perform subgroup audits, or provide a bias guarantee. Those are mandatory evaluation and governance tasks before any real hiring use.

## Testing and Evaluation

### What is tested today?

Unit tests cover strict requirement-schema transformation, basic resume sectioning, experience and cosine calibration helpers, alias matching, and short-skill false positives. CI runs Ruff and pytest on pushes and pull requests.

### What testing is still missing?

The repository does not yet include end-to-end document fixtures, embedding/FAISS integration tests, Streamlit smoke tests, PDF snapshot tests, or a labeled ranking-quality benchmark. These are important gaps to discuss honestly.

### How should ranking quality be evaluated?

Create a versioned set of job-description/resume pairs with multiple recruiter judgments. Measure NDCG@k, rank correlation, pairwise accuracy, requirement-extraction precision/recall, and score calibration. Evaluate failure cases and subgroup behavior separately; aggregate ranking metrics cannot establish fairness.

## Scaling Discussion

The current design is appropriate for an interactive, in-memory portfolio application. A larger system would first need measured workload and latency targets. Possible future changes include background embedding jobs, document-hash caching, persistent vectors, object storage, authentication, monitoring, and an API. A corpus-scale FAISS design or approximate index should only follow recall and latency benchmarks.

## Highest-Value Next Steps

1. Build a recruiter-labeled evaluation set and calibrate score weights.
2. Add OCR for image-only resumes.
3. Replace heuristic experience estimation with date-range parsing.
4. Expand and version the skill ontology.
5. Add integration tests and responsible-AI evaluation.

## Claims to Avoid

Do not describe the current project as bias-free, production-validated, fully offline, an autonomous hiring system, or a complete applicant-tracking system. Do not claim that FAISS indexes all candidates, that employment history is reconstructed, or that all personal attributes are removed. The strongest accurate claim is that the project demonstrates a transparent hybrid ranking design with a narrow LLM boundary and deterministic downstream scoring rules.
