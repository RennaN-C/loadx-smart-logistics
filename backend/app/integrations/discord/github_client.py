import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.integrations.discord.config import settings

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

PR_ISSUE_PATTERN = re.compile(
    r"\b(?:close[sd]?|fix(?:es|ed)?|resolve[sd]?)\s+#([0-9]+)\b",
    re.IGNORECASE,
)


HTML_COMMENT_PATTERN = re.compile(
    r"<!--.*?-->",
    re.DOTALL,
)

OC_TITLE_PATTERN = re.compile(
    r"^\[(OC[0-9]+)\](?:\s|$)",
    re.IGNORECASE,
)


@dataclass
class PullRequestInfo:
    url: str
    number: int | None = None
    title: str | None = None
    head_ref: str | None = None
    merged_at: str | None = None
    ci_status: str | None = None
    ci_url: str | None = None


@dataclass
class IssueProjectContext:
    issue_number: int
    issue_title: str
    issue_url: str
    issue_state: str
    issue_body: str

    responsible: str
    version: str
    branch: str | None
    assignees: list[str]

    project_id: str
    project_item_id: str

    status_field_id: str
    current_status: str | None

    status_options: dict[str, str]

    pr_url: str | None = None
    pr_number: int | None = None
    pr_merged_at: str | None = None
    issue_closed_at: str | None = None
    ci_status: str | None = None
    ci_url: str | None = None


PROJECT_ISSUE_QUERY = """
query(
  $owner: String!,
  $repository: String!,
  $issueNumber: Int!
) {
  repositoryOwner(login: $owner) {
    ... on User {
      projectsV2(first: 100) {
        nodes {
          id
          title

          fields(first: 100) {
            nodes {
              ... on ProjectV2SingleSelectField {
                id
                name

                options {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }

    ... on Organization {
      projectsV2(first: 100) {
        nodes {
          id
          title

          fields(first: 100) {
            nodes {
              ... on ProjectV2SingleSelectField {
                id
                name

                options {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }
  }

  repository(
    owner: $owner,
    name: $repository
  ) {
    issue(number: $issueNumber) {
      number
      title
      state
      url
      body
      closedAt

      milestone {
        title
      }

      assignees(first: 10) {
        nodes {
          login
        }
      }

      projectItems(first: 100) {
        nodes {
          id

          project {
            id
            title
          }

          fieldValues(first: 100) {
            nodes {
              ... on ProjectV2ItemFieldSingleSelectValue {
                name

                field {
                  ... on ProjectV2SingleSelectField {
                    id
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""


PROJECT_METADATA_QUERY = """
query($owner: String!) {
  repositoryOwner(login: $owner) {
    ... on User {
      projectsV2(first: 100) {
        nodes {
          id
          title

          fields(first: 100) {
            nodes {
              ... on ProjectV2SingleSelectField {
                id
                name

                options {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }

    ... on Organization {
      projectsV2(first: 100) {
        nodes {
          id
          title

          fields(first: 100) {
            nodes {
              ... on ProjectV2SingleSelectField {
                id
                name

                options {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }
  }
}
"""


PROJECT_ITEMS_QUERY = """
query($projectId: ID!) {
  node(id: $projectId) {
    ... on ProjectV2 {
      items(first: 100) {
        nodes {
          id

          content {
            ... on Issue {
              number
              title
              state
              url
              body
              closedAt

              milestone {
                title
              }

              assignees(first: 10) {
                nodes {
                  login
                }
              }
            }
          }

          fieldValues(first: 20) {
            nodes {
              ... on ProjectV2ItemFieldSingleSelectValue {
                name

                field {
                  ... on ProjectV2SingleSelectField {
                    id
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""


PULL_REQUESTS_QUERY = """
query(
  $owner: String!,
  $repository: String!,
  $cursor: String
) {
  repository(
    owner: $owner,
    name: $repository
  ) {
    pullRequests(
      first: 100,
      after: $cursor,
      baseRefName: "desenvolvimento",
      orderBy: {
        field: UPDATED_AT,
        direction: DESC
      }
    ) {
      nodes {
        number
        title
        url
        body
        updatedAt
        mergedAt
        baseRefName
        headRefName

        commits(last: 1) {
          nodes {
            commit {
              statusCheckRollup {
                state

                contexts(first: 100) {
                  nodes {
                    ... on CheckRun {
                      status
                      conclusion
                      detailsUrl
                    }

                    ... on StatusContext {
                      state
                      targetUrl
                    }
                  }
                }
              }
            }
          }
        }
      }

      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""


UPDATE_STATUS_MUTATION = """
mutation(
  $projectId: ID!,
  $itemId: ID!,
  $fieldId: ID!,
  $optionId: String!
) {
  updateProjectV2ItemFieldValue(
    input: {
      projectId: $projectId
      itemId: $itemId
      fieldId: $fieldId
      value: {
        singleSelectOptionId: $optionId
      }
    }
  ) {
    projectV2Item {
      id
    }
  }
}
"""


def _graphql(
    query: str,
    variables: dict[str, Any],
) -> dict[str, Any]:
    payload = json.dumps(
        {
            "query": query,
            "variables": variables,
        }
    ).encode("utf-8")

    request = Request(
        GITHUB_GRAPHQL_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.github_token}",
            "Content-Type": "application/json",
            "User-Agent": "LoadX-Discord-Bot",
        },
    )

    try:
        with urlopen(
            request,
            timeout=30,
        ) as response:
            result = json.loads(response.read().decode("utf-8"))

    except HTTPError as exc:
        body = exc.read().decode("utf-8")

        raise RuntimeError(f"GitHub respondeu HTTP {exc.code}: {body}") from exc

    errors = result.get("errors")

    if errors:
        raise RuntimeError(
            "Erro GraphQL: "
            + json.dumps(
                errors,
                ensure_ascii=False,
            )
        )

    data = result.get("data")

    if not isinstance(
        data,
        dict,
    ):
        raise TypeError("Resposta inválida da API do GitHub.")

    return data


def _extract_body_value(
    body: str,
    heading: str,
) -> str | None:
    lines = body.splitlines()

    target = f"## {heading}".strip().lower()

    for index, line in enumerate(lines):
        if line.strip().lower() != target:
            continue

        for value in lines[index + 1 :]:
            value = value.strip()

            if not value:
                continue

            if value.startswith("## "):
                return None

            return value.strip("`").strip()

    return None


def _get_responsible(
    body: str,
    assignees: list[str],
) -> str:
    responsible = _extract_body_value(
        body,
        "Responsável",
    )

    if responsible:
        return responsible

    if assignees:
        return f"@{assignees[0]}"

    return "Não atribuído"


def _extract_closing_issue_numbers(
    body: str,
) -> set[int]:
    visible_body = HTML_COMMENT_PATTERN.sub(
        "",
        body,
    )

    return {int(number) for number in PR_ISSUE_PATTERN.findall(visible_body)}


def _extract_oc_code(
    title: str,
) -> str | None:
    match = OC_TITLE_PATTERN.match(title.strip())

    if match is None:
        return None

    return match.group(1).upper()


def _pull_request_matches_issue(
    pull_request: PullRequestInfo,
    *,
    issue_title: str,
    branch: str | None,
) -> bool:
    issue_oc = _extract_oc_code(issue_title)

    if issue_oc is None:
        return True

    pr_oc = _extract_oc_code(pull_request.title or "")

    if pr_oc != issue_oc:
        return False

    if not branch:
        return False

    return pull_request.head_ref == branch


def _get_ci_details(
    pull_request: dict[str, Any],
) -> tuple[
    str | None,
    str | None,
]:
    commits = pull_request.get("commits") or {}

    commit_nodes = commits.get("nodes") or []

    if not commit_nodes:
        return None, None

    commit = commit_nodes[-1].get("commit") or {}

    rollup = commit.get("statusCheckRollup")

    if not rollup:
        return None, None

    state = rollup.get("state")

    if state == "SUCCESS":
        ci_status = "success"

    elif state in {
        "FAILURE",
        "ERROR",
    }:
        ci_status = "failure"

    else:
        ci_status = "pending"

    contexts = (rollup.get("contexts") or {}).get("nodes") or []

    candidate_urls: list[str] = []

    for context in contexts:
        url = context.get("detailsUrl") or context.get("targetUrl")

        if url:
            candidate_urls.append(url)

    ci_url = next(
        (url for url in candidate_urls if "/actions/runs/" in url),
        (candidate_urls[0] if candidate_urls else None),
    )

    if ci_url is None:
        ci_url = f"{pull_request['url']}/checks"

    return (
        ci_status,
        ci_url,
    )


def _get_pull_request_info() -> dict[
    int,
    PullRequestInfo,
]:
    result: dict[
        int,
        PullRequestInfo,
    ] = {}

    latest_updates: dict[
        int,
        str,
    ] = {}

    cursor = None

    while True:
        data = _graphql(
            PULL_REQUESTS_QUERY,
            {
                "owner": settings.github_owner,
                "repository": (settings.github_repository),
                "cursor": cursor,
            },
        )

        repository = data.get("repository")

        if repository is None:
            return result

        pull_requests = repository["pullRequests"]

        for pull_request in pull_requests["nodes"]:
            if pull_request.get("baseRefName") != "desenvolvimento":
                continue

            issue_numbers = _extract_closing_issue_numbers(
                pull_request.get("body") or ""
            )

            # O contrato do LoadX permite exatamente uma Issue
            # por Pull Request. PR inválido não deve contaminar
            # nenhum card enquanto aguarda correção.
            if len(issue_numbers) != 1:
                continue

            updated_at = pull_request["updatedAt"]

            (
                ci_status,
                ci_url,
            ) = _get_ci_details(pull_request)

            for issue_number in issue_numbers:
                if (
                    issue_number not in result
                    or updated_at > latest_updates[issue_number]
                ):
                    result[issue_number] = PullRequestInfo(
                        url=pull_request["url"],
                        number=pull_request.get("number"),
                        title=pull_request.get("title"),
                        head_ref=pull_request.get("headRefName"),
                        merged_at=pull_request.get("mergedAt"),
                        ci_status=ci_status,
                        ci_url=ci_url,
                    )

                    latest_updates[issue_number] = updated_at

        page_info = pull_requests["pageInfo"]

        if not page_info["hasNextPage"]:
            return result

        cursor = page_info["endCursor"]


def _get_pull_request_urls() -> dict[
    int,
    str,
]:
    return {
        issue_number: info.url
        for issue_number, info in _get_pull_request_info().items()
    }


def get_issue_context(
    issue_number: int,
) -> IssueProjectContext:
    data = _graphql(
        PROJECT_ISSUE_QUERY,
        {
            "owner": settings.github_owner,
            "repository": (settings.github_repository),
            "issueNumber": issue_number,
        },
    )

    owner = data.get("repositoryOwner")

    if owner is None:
        raise RuntimeError("Owner do GitHub não encontrado.")

    projects = owner["projectsV2"]["nodes"]

    project = next(
        (item for item in projects if item["title"] == settings.github_project_title),
        None,
    )

    if project is None:
        raise RuntimeError(f"Project não encontrado: {settings.github_project_title}")

    status_field = next(
        (
            field
            for field in project["fields"]["nodes"]
            if field.get("name") == settings.github_status_field
        ),
        None,
    )

    if status_field is None:
        raise RuntimeError(
            f"Campo de status não encontrado: {settings.github_status_field}"
        )

    repository = data.get("repository")

    if repository is None:
        raise RuntimeError("Repositório não encontrado.")

    issue = repository.get("issue")

    if issue is None:
        raise RuntimeError(f"Issue #{issue_number} não encontrada.")

    project_item = next(
        (
            item
            for item in issue["projectItems"]["nodes"]
            if item["project"]["id"] == project["id"]
        ),
        None,
    )

    if project_item is None:
        raise RuntimeError(f"Issue #{issue_number} não está no Project.")

    current_status = None

    for value in project_item["fieldValues"]["nodes"]:
        field = value.get("field")

        if not field:
            continue

        if field.get("name") == settings.github_status_field:
            current_status = value.get("name")

            break

    status_options = {
        option["name"]: option["id"] for option in status_field["options"]
    }

    body = issue.get("body") or ""

    assignees = [item["login"] for item in issue["assignees"]["nodes"]]

    responsible = _get_responsible(
        body,
        assignees,
    )

    milestone = issue.get("milestone")

    version = milestone["title"] if milestone else settings.github_target_milestone

    branch = _extract_body_value(
        body,
        "Branch sugerida",
    )

    pull_request_info = _get_pull_request_info()

    pr_info = pull_request_info.get(issue["number"])

    if pr_info is not None and not _pull_request_matches_issue(
        pr_info,
        issue_title=issue["title"],
        branch=branch,
    ):
        pr_info = None

    return IssueProjectContext(
        issue_number=issue["number"],
        issue_title=issue["title"],
        issue_url=issue["url"],
        issue_state=issue["state"],
        issue_body=body,
        responsible=responsible,
        version=version,
        branch=branch,
        assignees=assignees,
        project_id=project["id"],
        project_item_id=project_item["id"],
        status_field_id=status_field["id"],
        current_status=current_status,
        status_options=status_options,
        pr_url=(pr_info.url if pr_info else None),
        pr_number=(pr_info.number if pr_info else None),
        pr_merged_at=(pr_info.merged_at if pr_info else None),
        issue_closed_at=issue.get("closedAt"),
        ci_status=(pr_info.ci_status if pr_info else None),
        ci_url=(pr_info.ci_url if pr_info else None),
    )


def list_project_issues(
    milestone: str | None = None,
) -> list[IssueProjectContext]:
    target_milestone = milestone or settings.github_target_milestone

    metadata = _graphql(
        PROJECT_METADATA_QUERY,
        {
            "owner": settings.github_owner,
        },
    )

    owner = metadata.get("repositoryOwner")

    if owner is None:
        raise RuntimeError("Owner do GitHub não encontrado.")

    project = next(
        (
            item
            for item in owner["projectsV2"]["nodes"]
            if item["title"] == settings.github_project_title
        ),
        None,
    )

    if project is None:
        raise RuntimeError(f"Project não encontrado: {settings.github_project_title}")

    status_field = next(
        (
            field
            for field in project["fields"]["nodes"]
            if field.get("name") == settings.github_status_field
        ),
        None,
    )

    if status_field is None:
        raise RuntimeError(
            f"Campo de status não encontrado: {settings.github_status_field}"
        )

    status_options = {
        option["name"]: option["id"] for option in status_field["options"]
    }

    items_data = _graphql(
        PROJECT_ITEMS_QUERY,
        {
            "projectId": project["id"],
        },
    )

    node = items_data.get("node")

    if node is None:
        raise RuntimeError("Project não encontrado pelo ID.")

    pull_request_info = _get_pull_request_info()

    issues: list[IssueProjectContext] = []

    for project_item in node["items"]["nodes"]:
        issue = project_item.get("content")

        if not issue:
            continue

        issue_number = issue.get("number")

        if issue_number is None:
            continue

        milestone_data = issue.get("milestone")

        version = milestone_data["title"] if milestone_data else "Não informada"

        if target_milestone and version != target_milestone:
            continue

        body = issue.get("body") or ""

        assignees = [item["login"] for item in issue["assignees"]["nodes"]]

        responsible = _get_responsible(
            body,
            assignees,
        )

        branch = _extract_body_value(
            body,
            "Branch sugerida",
        )

        current_status = None

        for value in project_item["fieldValues"]["nodes"]:
            field = value.get("field")

            if not field:
                continue

            if field.get("name") == settings.github_status_field:
                current_status = value.get("name")

                break

        pr_info = pull_request_info.get(issue["number"])

        if pr_info is not None and not _pull_request_matches_issue(
            pr_info,
            issue_title=issue["title"],
            branch=branch,
        ):
            pr_info = None

        issues.append(
            IssueProjectContext(
                issue_number=issue["number"],
                issue_title=issue["title"],
                issue_url=issue["url"],
                issue_state=issue["state"],
                issue_body=body,
                responsible=responsible,
                version=version,
                branch=branch,
                assignees=assignees,
                project_id=project["id"],
                project_item_id=(project_item["id"]),
                status_field_id=(status_field["id"]),
                current_status=(current_status),
                status_options=(status_options.copy()),
                pr_url=(pr_info.url if pr_info else None),
                pr_number=(pr_info.number if pr_info else None),
                pr_merged_at=(pr_info.merged_at if pr_info else None),
                issue_closed_at=issue.get("closedAt"),
                ci_status=(pr_info.ci_status if pr_info else None),
                ci_url=(pr_info.ci_url if pr_info else None),
            )
        )

    return sorted(
        issues,
        key=lambda item: item.issue_number,
    )


def update_issue_status(
    issue_number: int,
    target_status: str,
) -> IssueProjectContext:
    context = get_issue_context(issue_number)

    if context.current_status == target_status:
        return context

    option_id = context.status_options.get(target_status)

    if option_id is None:
        raise RuntimeError(f"Status não encontrado no Project: {target_status}")

    _graphql(
        UPDATE_STATUS_MUTATION,
        {
            "projectId": (context.project_id),
            "itemId": (context.project_item_id),
            "fieldId": (context.status_field_id),
            "optionId": option_id,
        },
    )

    context.current_status = target_status

    return context
