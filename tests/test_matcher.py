import pytest

from src.ranking.matcher import lexical_overlap, partition_matches, term_present


def test_term_present_handles_common_alias():
    assert term_present("Amazon Web Services", "Deployed models using AWS Lambda")


def test_partition_matches():
    matched, missing = partition_matches(["Python", "Kubernetes"], "Python and Docker")
    assert matched == ["Python"]
    assert missing == ["Kubernetes"]


def test_lexical_overlap_is_bounded():
    assert lexical_overlap(["Python", "SQL"], "Python developer") == 0.5


@pytest.mark.parametrize(
    "text",
    ["R", "R programming", "R language", "RStudio", "programming in R"],
)
def test_r_matches_standalone_and_aliases(text):
    assert term_present("R", text)


@pytest.mark.parametrize(
    "text",
    ["researcher", "required", "years", "developer", "project"],
)
def test_r_does_not_match_inside_words(text):
    assert not term_present("R", text)


def test_partition_does_not_report_r_from_unrelated_words():
    matched, missing = partition_matches(
        ["R"], "Researcher with years of required developer project experience"
    )
    assert matched == []
    assert missing == ["R"]


@pytest.mark.parametrize(
    ("skill", "text"),
    [
        ("C", "C programming"),
        ("C++", "C++ development"),
        ("C++", "Modern CPP development"),
        ("C#", "C# development"),
        ("C#", "C Sharp development"),
        ("Go", "Go services"),
        (".NET", ".NET APIs"),
        (".NET", "dotnet APIs"),
        (".NET", "ASP.NET APIs"),
        ("Node.js", "Node.js services"),
        ("Node.js", "NodeJS services"),
        ("React.js", "React.js frontend"),
        ("React.js", "ReactJS frontend"),
        ("React.js", "React frontend"),
    ],
)
def test_boundary_aware_skill_aliases(skill, text):
    assert term_present(skill, text)


@pytest.mark.parametrize(
    ("skill", "text"),
    [
        ("C", "C++ and C# development"),
        ("Go", "Google and Django"),
        (".NET", "internet protocols"),
        ("Node.js", "NodeJSDeveloper"),
        ("React.js", "reactive systems"),
    ],
)
def test_boundary_aware_skills_do_not_match_larger_terms(skill, text):
    assert not term_present(skill, text)
