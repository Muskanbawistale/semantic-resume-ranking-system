from __future__ import annotations

import re
from collections.abc import Iterable
from functools import lru_cache

from src.utils.text import normalize_term


SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "R": ("R", "R programming", "R language", "RStudio"),
    "C": ("C",),
    "C++": ("C++", "CPP"),
    "C#": ("C#", "C Sharp"),
    "Go": ("Go",),
    ".NET": (".NET", "dotnet", "ASP.NET"),
    "Node.js": ("Node.js", "NodeJS"),
    "React.js": ("React.js", "ReactJS", "React"),
}

_GENERAL_ALIAS_GROUPS: tuple[tuple[str, ...], ...] = (
    ("Amazon Web Services", "AWS"),
    ("Machine Learning", "ML"),
    ("Artificial Intelligence", "AI"),
    ("Natural Language Processing", "NLP"),
    ("Google Cloud Platform", "GCP"),
    ("Continuous Integration", "CI"),
    ("Continuous Deployment", "CD"),
)

_ALIAS_GROUPS = (*SKILL_ALIASES.values(), *_GENERAL_ALIAS_GROUPS)
_ALIASES_BY_NORMALIZED = {
    normalize_term(alias): group for group in _ALIAS_GROUPS for alias in group
}


@lru_cache(maxsize=None)
def _boundary_pattern(alias: str) -> re.Pattern[str]:
    escaped_alias = r"\s+".join(re.escape(part) for part in alias.split())
    right_boundary = r"(?![A-Za-z0-9])"
    if alias.casefold() == "c":
        right_boundary = r"(?![A-Za-z0-9+#])"
    return re.compile(
        rf"(?<![A-Za-z0-9]){escaped_alias}{right_boundary}",
        flags=re.IGNORECASE,
    )


def term_present(term: str, text: str) -> bool:
    normalized = normalize_term(term)
    if not normalized:
        return False
    alias_group = _ALIASES_BY_NORMALIZED.get(normalized, ())
    aliases = tuple(dict.fromkeys((term, *alias_group)))
    return any(_boundary_pattern(alias).search(text) is not None for alias in aliases)


def partition_matches(terms: Iterable[str], text: str) -> tuple[list[str], list[str]]:
    matched, missing = [], []
    for term in terms:
        (matched if term_present(term, text) else missing).append(term)
    return matched, missing


def lexical_overlap(query_terms: Iterable[str], text: str) -> float:
    terms = list(query_terms)
    if not terms:
        return 1.0
    tokens = set(re.findall(r"[a-z0-9+#.]+", text.lower()))
    hits = sum(any(tok in tokens for tok in re.findall(r"[a-z0-9+#.]+", term.lower())) for term in terms)
    return hits / len(terms)
