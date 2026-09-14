from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Any

HTML_COMMENT_PATTERN = re.compile(
    r"<!--.*?-->",
    re.DOTALL,
)

CLOSING_PATTERN = re.compile(
    r"\b(?:close[sd]?|fix(?:es|ed)?|resolve[sd]?)\s+#([0-9]+)\b",
    re.IGNORECASE,
)

OC_TITLE_PATTERN = re.compile(
    r"^\[(OC[0-9]+)\](?:\s|$)",
    re.IGNORECASE,
)

IDENTIFIER_PATTERN = re.compile(
    r"^\s*Identificador:\s*([^\s]+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


class ValidationError(Exception):
    pass


def visible_text(text: str) -> str:
    return HTML_COMMENT_PATTERN.sub("", text)


def extract_closing_issue_numbers(
    body: str,
) -> list[int]:
    body = visible_text(body)

    return sorted({int(number) for number in CLOSING_PATTERN.findall(body)})


def extract_identifier(
    body: str,
) -> str:
    body = visible_text(body)

    matches = IDENTIFIER_PATTERN.findall(body)

    if len(matches) != 1:
        raise ValidationError(
            "O PR deve possuir exatamente uma linha "
            "'Identificador: OCXX' ou 'Identificador: N/A'."
        )

    return matches[0].upper()


def extract_heading_value(
    body: str,
    heading: str,
) -> str | None:
    lines = body.splitlines()
    target = f"## {heading}".strip().casefold()

    for index, line in enumerate(lines):
        if line.strip().casefold() != target:
            continue

        for value in lines[index + 1 :]:
            value = value.strip()

            if not value:
                continue

            if value.startswith("## "):
                return None

            return value.strip("`").strip()

    return None


def validate_contract(
    *,
    pr_body: str,
    pr_title: str,
    head_ref: str,
    issue_number: int,
    issue: dict[str, Any],
    project_titles: set[str],
    project_title: str,
    target_milestone: str,
    allow_closed_issue: bool = False,
) -> None:
    linked_numbers = extract_closing_issue_numbers(pr_body)

    if linked_numbers != [issue_number]:
        raise ValidationError(
            "O PR deve vincular exatamente uma Issue com Closes/Fixes/Resolves #NUMERO."
        )

    identifier = extract_identifier(pr_body)

    if issue.get("pull_request") is not None:
        raise ValidationError(f"#{issue_number} é um Pull Request, não uma Issue.")

    issue_state = issue.get("state")

    if issue_state != "open":
        closed_after_merge = allow_closed_issue and issue_state == "closed"

        if not closed_after_merge:
            raise ValidationError(f"A Issue #{issue_number} precisa estar aberta.")

    issue_title = str(issue.get("title") or "").strip()

    oc_match = OC_TITLE_PATTERN.match(issue_title)

    # Trabalho de infraestrutura que não é uma OC.
    if oc_match is None:
        if identifier != "N/A":
            raise ValidationError(
                "A Issue vinculada não é uma OC. Use 'Identificador: N/A'."
            )

        return

    oc_code = oc_match.group(1).upper()

    if identifier != oc_code:
        raise ValidationError(
            f"Identificador do PR ({identifier}) não corresponde à Issue [{oc_code}]."
        )

    pr_match = OC_TITLE_PATTERN.match(pr_title.strip())

    if pr_match is None:
        raise ValidationError(f"O título do PR deve começar com '[{oc_code}]'.")

    if pr_match.group(1).upper() != oc_code:
        raise ValidationError(
            f"O título do PR referencia "
            f"{pr_match.group(1).upper()}, "
            f"mas a Issue é {oc_code}."
        )

    milestone = issue.get("milestone")

    milestone_title = milestone.get("title") if isinstance(milestone, dict) else None

    if milestone_title != target_milestone:
        raise ValidationError(
            f"A Issue {oc_code} precisa estar no "
            f"milestone '{target_milestone}'. "
            f"Atual: "
            f"'{milestone_title or 'nenhum'}'."
        )

    expected_branch = extract_heading_value(
        str(issue.get("body") or ""),
        "Branch sugerida",
    )

    if not expected_branch:
        raise ValidationError(
            f"A Issue {oc_code} não possui '## Branch sugerida' preenchida."
        )

    if head_ref != expected_branch:
        raise ValidationError(
            f"Branch incorreta. Esperada: '{expected_branch}'. Atual: '{head_ref}'."
        )

    responsible = extract_heading_value(
        str(issue.get("body") or ""),
        "Responsável",
    )

    assignees = issue.get("assignees") or []

    if not responsible and not assignees:
        raise ValidationError(
            f"A Issue {oc_code} precisa possuir responsável no corpo ou assignee."
        )

    if project_title not in project_titles:
        raise ValidationError(
            f"A Issue {oc_code} precisa estar no Project '{project_title}'."
        )


def gh_json(
    *args: str,
) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["gh", "api", *args],
            check=True,
            capture_output=True,
            text=True,
        )

    except FileNotFoundError as exc:
        raise ValidationError("GitHub CLI (gh) não está disponível.") from exc

    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()

        raise ValidationError(
            "Falha ao consultar GitHub API" + (f": {stderr}" if stderr else ".")
        ) from exc

    try:
        payload = json.loads(result.stdout)

    except json.JSONDecodeError as exc:
        raise ValidationError("GitHub API retornou JSON inválido.") from exc

    if not isinstance(payload, dict):
        raise ValidationError("GitHub API retornou estrutura inesperada.")

    return payload


def get_project_titles(
    issue_node_id: str,
) -> set[str]:
    query = """
    query($issueId: ID!) {
      node(id: $issueId) {
        ... on Issue {
          projectItems(first: 100) {
            nodes {
              project {
                title
              }
            }
          }
        }
      }
    }
    """

    payload = gh_json(
        "graphql",
        "-f",
        f"query={query}",
        "-F",
        f"issueId={issue_node_id}",
    )

    nodes = (
        payload.get("data", {}).get("node", {}).get("projectItems", {}).get("nodes", [])
    )

    return {
        str(item["project"]["title"])
        for item in nodes
        if isinstance(item, dict)
        and isinstance(
            item.get("project"),
            dict,
        )
        and item["project"].get("title")
    }


def main() -> int:
    pr_body = os.environ.get(
        "PR_BODY",
        "",
    )

    pr_title = os.environ.get(
        "PR_TITLE",
        "",
    )

    head_ref = os.environ.get(
        "PR_HEAD_REF",
        "",
    )

    repository = os.environ.get(
        "REPOSITORY",
        "",
    )

    project_title = os.environ.get(
        "PROJECT_TITLE",
        "LoadX — Desenvolvimento",
    )

    target_milestone = os.environ.get(
        "TARGET_MILESTONE",
        "v1.1.0",
    )

    allow_closed_issue = (
        os.environ.get(
            "ALLOW_CLOSED_ISSUE",
            "false",
        ).lower()
        == "true"
    )

    try:
        linked_numbers = extract_closing_issue_numbers(pr_body)

        if len(linked_numbers) != 1:
            raise ValidationError(
                "O PR deve conter exatamente "
                "uma Issue vinculada. "
                "Exemplo: 'Closes #NUMERO'."
            )

        issue_number = linked_numbers[0]

        issue = gh_json(f"repos/{repository}/issues/{issue_number}")

        issue_title = str(issue.get("title") or "")

        project_titles: set[str] = set()

        if OC_TITLE_PATTERN.match(issue_title.strip()):
            issue_node_id = str(issue.get("node_id") or "")

            if not issue_node_id:
                raise ValidationError("Não foi possível obter o node_id da Issue.")

            project_titles = get_project_titles(issue_node_id)

        validate_contract(
            pr_body=pr_body,
            pr_title=pr_title,
            head_ref=head_ref,
            issue_number=issue_number,
            issue=issue,
            project_titles=project_titles,
            project_title=project_title,
            target_milestone=target_milestone,
            allow_closed_issue=(allow_closed_issue),
        )

        github_output = os.environ.get("GITHUB_OUTPUT")

        if github_output:
            with open(
                github_output,
                "a",
                encoding="utf-8",
            ) as output:
                output.write(f"issue_number={issue_number}\n")

    except ValidationError as exc:
        print(f"::error::{exc}")
        print()
        print("Contrato esperado para uma OC:")
        print("  Título: [OCXX] descrição")
        print("  Corpo: Closes #NUMERO")
        print("         Identificador: OCXX")
        print("  Branch: a definida na Issue")

        return 1

    print(f"Contrato do PR validado com sucesso: Issue #{issue_number}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
