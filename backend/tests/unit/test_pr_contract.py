from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "scripts"
    / "validate_pr_contract.py"
)

spec = importlib.util.spec_from_file_location(
    "validate_pr_contract",
    SCRIPT,
)

assert spec is not None
assert spec.loader is not None

validator = importlib.util.module_from_spec(spec)

spec.loader.exec_module(validator)


def oc_issue() -> dict:
    return {
        "title": ("[OC64] Regra de conflito de caminhões"),
        "state": "open",
        "body": (
            "## Responsável\n"
            "Rennan — DEV 1\n\n"
            "## Branch sugerida\n"
            "`rennan/oc64-conflito-caminhoes`\n"
        ),
        "milestone": {
            "title": "v1.1.0",
        },
        "assignees": [],
    }


def validate(
    *,
    pr_body: str = ("Closes #46\n\nIdentificador: OC64"),
    pr_title: str = ("[OC64] Regra de conflito de caminhões"),
    head_ref: str = ("rennan/oc64-conflito-caminhoes"),
    issue: dict | None = None,
    projects: set[str] | None = None,
    allow_closed_issue: bool = False,
) -> None:
    validator.validate_contract(
        pr_body=pr_body,
        pr_title=pr_title,
        head_ref=head_ref,
        issue_number=46,
        issue=issue or oc_issue(),
        project_titles=(
            projects if projects is not None else {"LoadX — Desenvolvimento"}
        ),
        project_title=("LoadX — Desenvolvimento"),
        target_milestone="v1.1.0",
        allow_closed_issue=(allow_closed_issue),
    )


def test_extracts_supported_closing_keywords() -> None:
    body = "Closes #46\nFixes #47\nResolves #48\ncloses #46"

    assert validator.extract_closing_issue_numbers(body) == [46, 47, 48]


def test_html_comments_are_ignored() -> None:
    body = (
        "<!-- Closes #999 -->\n"
        "Closes #46\n"
        "<!-- Identificador: OC99 -->\n"
        "Identificador: OC64"
    )

    assert validator.extract_closing_issue_numbers(body) == [46]

    assert validator.extract_identifier(body) == "OC64"


def test_valid_oc_contract_passes() -> None:
    validate()


def test_wrong_identifier_fails() -> None:
    with pytest.raises(
        validator.ValidationError,
        match="não corresponde",
    ):
        validate(pr_body=("Closes #46\n\nIdentificador: OC65"))


def test_wrong_branch_fails() -> None:
    with pytest.raises(
        validator.ValidationError,
        match="Branch incorreta",
    ):
        validate(head_ref="rennan/outra-branch")


def test_wrong_pr_title_fails() -> None:
    with pytest.raises(
        validator.ValidationError,
        match="título do PR",
    ):
        validate(pr_title=("[OC65] Outra ocorrência"))


def test_missing_project_fails() -> None:
    with pytest.raises(
        validator.ValidationError,
        match="Project",
    ):
        validate(projects=set())


def test_wrong_milestone_fails() -> None:
    issue = oc_issue()

    issue["milestone"] = {
        "title": "v1.2.0",
    }

    with pytest.raises(
        validator.ValidationError,
        match="milestone",
    ):
        validate(issue=issue)


def test_non_oc_requires_na_identifier() -> None:
    issue = {
        "title": "[CI] Validação de PR",
        "state": "open",
        "body": "",
        "milestone": None,
        "assignees": [],
    }

    validator.validate_contract(
        pr_body=("Closes #77\n\nIdentificador: N/A"),
        pr_title="[CI] Validação de PR",
        head_ref="rennan/validacao-pr",
        issue_number=77,
        issue=issue,
        project_titles=set(),
        project_title=("LoadX — Desenvolvimento"),
        target_milestone="v1.1.0",
    )


def test_multiple_issues_fail() -> None:
    with pytest.raises(
        validator.ValidationError,
        match="exatamente uma Issue",
    ):
        validate(pr_body=("Closes #46\nFixes #47\n\nIdentificador: OC64"))


def test_closed_issue_fails_before_merge() -> None:
    issue = oc_issue()
    issue["state"] = "closed"

    with pytest.raises(
        validator.ValidationError,
        match="precisa estar aberta",
    ):
        validate(issue=issue)


def test_closed_issue_is_allowed_after_merge() -> None:
    issue = oc_issue()
    issue["state"] = "closed"

    validate(
        issue=issue,
        allow_closed_issue=True,
    )
