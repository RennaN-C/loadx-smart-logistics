import asyncio
import importlib
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import discord
import pytest

PR_URL = "https://github.com/example/logistics/pull/63"

CI_URL = "https://github.com/example/logistics/actions/runs/123456789"


@pytest.fixture(scope="module")
def discord_modules():
    # Import the real modules without loading .env files or Docker secrets.
    config = ModuleType("app.integrations.discord.config")

    config.settings = SimpleNamespace(
        github_owner="example",
        github_repository="logistics",
        github_project_title="Test Project",
        github_status_field="Status",
        github_target_milestone="v1.1.0",
        discord_tasks_channel_id=998,
        discord_completed_channel_id=997,
        discord_status_channel_id=999,
        discord_guild_id=996,
        discord_owner_user_id=1,
        discord_rennan_user_id=2,
        discord_joao_user_id=3,
        discord_marlon_user_id=4,
        discord_marcelo_user_id=5,
    )

    with patch.dict(
        sys.modules,
        {
            config.__name__: config,
        },
    ):
        github = importlib.import_module("app.integrations.discord.github_client")

        bot = importlib.import_module("app.integrations.discord.bot")

        cards = importlib.import_module("app.integrations.discord.cards")

        yield SimpleNamespace(
            github=github,
            bot=bot,
            cards=cards,
        )


@pytest.fixture(autouse=True)
def no_external_calls(
    discord_modules,
    monkeypatch,
):
    github_http = Mock(side_effect=AssertionError("GitHub HTTP is forbidden"))

    discord_http = AsyncMock(side_effect=AssertionError("Discord HTTP is forbidden"))

    status_update = Mock(side_effect=AssertionError("Status changes are forbidden"))

    monkeypatch.setattr(
        discord_modules.github,
        "urlopen",
        github_http,
    )

    monkeypatch.setattr(
        discord.http.HTTPClient,
        "request",
        discord_http,
    )

    monkeypatch.setattr(
        discord_modules.bot,
        "update_issue_status",
        status_update,
    )

    yield

    github_http.assert_not_called()
    discord_http.assert_not_called()
    status_update.assert_not_called()


def pull_request(
    body="Closes #44",
    *,
    base="desenvolvimento",
    url=PR_URL,
    number=63,
    title="[OC62] Tarefa de teste",
    head_ref="feature/test",
    updated_at="2026-09-13T12:00:00Z",
    merged_at=None,
    ci_state=None,
    ci_url=None,
):
    result = {
        "number": number,
        "title": title,
        "body": body,
        "baseRefName": base,
        "headRefName": head_ref,
        "url": url,
        "updatedAt": updated_at,
        "mergedAt": merged_at,
    }

    if ci_state is None:
        result["commits"] = {
            "nodes": [],
        }

        return result

    contexts = []

    if ci_url:
        contexts.append(
            {
                "status": "COMPLETED",
                "conclusion": ci_state,
                "detailsUrl": ci_url,
            }
        )

    result["commits"] = {
        "nodes": [
            {
                "commit": {
                    "statusCheckRollup": {
                        "state": ci_state,
                        "contexts": {
                            "nodes": contexts,
                        },
                    }
                }
            }
        ]
    }

    return result


def pull_request_page(
    nodes,
    *,
    cursor=None,
):
    return {
        "repository": {
            "pullRequests": {
                "nodes": nodes,
                "pageInfo": {
                    "hasNextPage": (cursor is not None),
                    "endCursor": cursor,
                },
            }
        }
    }


def issue_context(
    discord_modules,
    *,
    pr_url=None,
    pr_number=None,
    pr_merged_at=None,
    issue_closed_at=None,
    ci_status=None,
    ci_url=None,
    status="Em revisão",
    assignees=None,
):
    if assignees is None:
        assignees = [
            "test-user",
        ]

    return discord_modules.github.IssueProjectContext(
        issue_number=44,
        issue_title=("[OC62] Tarefa de teste"),
        issue_url=("https://github.com/example/logistics/issues/44"),
        issue_state="OPEN",
        issue_body="",
        responsible=("Pessoa de teste"),
        version="v1.1.0",
        branch="feature/test",
        assignees=assignees,
        project_id="test-project",
        project_item_id="test-item",
        status_field_id=("test-status-field"),
        current_status=status,
        status_options={},
        pr_url=pr_url,
        pr_number=pr_number,
        pr_merged_at=pr_merged_at,
        issue_closed_at=issue_closed_at,
        ci_status=ci_status,
        ci_url=ci_url,
    )


@pytest.mark.parametrize(
    "keyword",
    [
        "Close",
        "Closes",
        "Closed",
        "Fix",
        "Fixes",
        "Fixed",
        "Resolve",
        "Resolves",
        "Resolved",
        "cLoSeS",
        "FIXES",
        "rEsOlVeS",
    ],
)
def test_closing_keywords(
    discord_modules,
    keyword,
):
    assert discord_modules.github._extract_closing_issue_numbers(f"{keyword} #44") == {
        44
    }


def test_multiple_issues_and_duplicate_references(
    discord_modules,
):
    body = "## Entrega\nCloses #46\nFixes #47\nResolves #48\nCloses #46"

    assert discord_modules.github._extract_closing_issue_numbers(body) == {
        46,
        47,
        48,
    }


@pytest.mark.parametrize(
    "body",
    [
        "",
        "Relacionado a #44",
        "Discloses #44",
        "Closes other/repo#44",
    ],
)
def test_non_closing_references_are_ignored(
    discord_modules,
    body,
):
    assert discord_modules.github._extract_closing_issue_numbers(body) == set()


def test_mapping_uses_body_and_ignores_other_bases(
    discord_modules,
    monkeypatch,
):
    github = discord_modules.github

    graphql = Mock(
        return_value=pull_request_page(
            [
                pull_request("Closes #44"),
                pull_request(
                    "Fixes #44\nResolves #46",
                    base="main",
                    url=PR_URL + "0",
                ),
                pull_request(None),
            ]
        )
    )

    monkeypatch.setattr(
        github,
        "_graphql",
        graphql,
    )

    assert github._get_pull_request_urls() == {
        44: PR_URL,
    }

    graphql.assert_called_once_with(
        github.PULL_REQUESTS_QUERY,
        {
            "owner": "example",
            "repository": "logistics",
            "cursor": None,
        },
    )

    assert 'baseRefName: "desenvolvimento"' in github.PULL_REQUESTS_QUERY

    assert "body" in github.PULL_REQUESTS_QUERY

    assert "closingIssuesReferences" not in github.PULL_REQUESTS_QUERY


def test_latest_updated_pr_wins_across_pages(
    discord_modules,
    monkeypatch,
):
    github = discord_modules.github

    latest_url = "https://github.com/example/logistics/pull/66"

    graphql = Mock(
        side_effect=[
            pull_request_page(
                [
                    pull_request(
                        updated_at=("2026-09-11T12:00:00Z"),
                    ),
                ],
                cursor="next-page",
            ),
            pull_request_page(
                [
                    pull_request(
                        "Fixes #44",
                        url=latest_url,
                    ),
                    pull_request(
                        updated_at=("2026-09-10T12:00:00Z"),
                    ),
                ]
            ),
        ]
    )

    monkeypatch.setattr(
        github,
        "_graphql",
        graphql,
    )

    assert github._get_pull_request_urls() == {
        44: latest_url,
    }

    assert [call.args[1]["cursor"] for call in graphql.call_args_list] == [
        None,
        "next-page",
    ]

    assert "after: $cursor" in github.PULL_REQUESTS_QUERY


@pytest.mark.parametrize(
    (
        "rollup_state",
        "expected_status",
    ),
    [
        (
            "SUCCESS",
            "success",
        ),
        (
            "FAILURE",
            "failure",
        ),
        (
            "ERROR",
            "failure",
        ),
        (
            "PENDING",
            "pending",
        ),
        (
            "EXPECTED",
            "pending",
        ),
    ],
)
def test_ci_rollup_state_mapping(
    discord_modules,
    rollup_state,
    expected_status,
):
    github = discord_modules.github

    pr = pull_request(
        ci_state=rollup_state,
    )

    (
        ci_status,
        ci_url,
    ) = github._get_ci_details(pr)

    assert ci_status == expected_status

    assert ci_url == f"{PR_URL}/checks"


def test_ci_details_prefers_actions_run_url(
    discord_modules,
):
    github = discord_modules.github

    pr = pull_request(
        ci_state="SUCCESS",
        ci_url=CI_URL,
    )

    (
        ci_status,
        ci_url,
    ) = github._get_ci_details(pr)

    assert ci_status == "success"
    assert ci_url == CI_URL


def test_ci_details_without_rollup(
    discord_modules,
):
    github = discord_modules.github

    pr = pull_request()

    (
        ci_status,
        ci_url,
    ) = github._get_ci_details(pr)

    assert ci_status is None
    assert ci_url is None


def test_pull_request_info_includes_ci(
    discord_modules,
    monkeypatch,
):
    github = discord_modules.github

    graphql = Mock(
        return_value=pull_request_page(
            [
                pull_request(
                    "Closes #44",
                    ci_state="SUCCESS",
                    ci_url=CI_URL,
                )
            ]
        )
    )

    monkeypatch.setattr(
        github,
        "_graphql",
        graphql,
    )

    result = github._get_pull_request_info()

    assert 44 in result

    info = result[44]

    assert info.url == PR_URL
    assert info.ci_status == "success"
    assert info.ci_url == CI_URL


@pytest.mark.parametrize(
    "lookup",
    [
        "single",
        "list",
    ],
)
@pytest.mark.parametrize(
    "has_pr",
    [
        True,
        False,
    ],
)
def test_public_context_includes_optional_pr(
    discord_modules,
    monkeypatch,
    lookup,
    has_pr,
):
    github = discord_modules.github

    project = {
        "id": "test-project",
        "title": "Test Project",
        "fields": {
            "nodes": [
                {
                    "id": ("test-status-field"),
                    "name": "Status",
                    "options": [],
                }
            ]
        },
    }

    item = {
        "id": "test-item",
        "project": {
            "id": project["id"],
        },
        "fieldValues": {
            "nodes": [
                {
                    "name": "Em revisão",
                    "field": {
                        "name": "Status",
                    },
                }
            ]
        },
    }

    issue = {
        "number": 44,
        "title": ("[OC62] Tarefa de teste"),
        "url": ("https://github.com/example/logistics/issues/44"),
        "state": "OPEN",
        "body": ("## Branch sugerida\n`feature/test`\n"),
        "milestone": {
            "title": "v1.1.0",
        },
        "assignees": {
            "nodes": [
                {
                    "login": "test-user",
                }
            ]
        },
        "projectItems": {
            "nodes": [
                item,
            ]
        },
    }

    metadata = {
        "repositoryOwner": {
            "projectsV2": {
                "nodes": [
                    project,
                ]
            }
        }
    }

    pull_requests = [pull_request("Closes #44")] if has_pr else []

    responses = {
        github.PROJECT_ISSUE_QUERY: {
            **metadata,
            "repository": {
                "issue": issue,
            },
        },
        github.PROJECT_METADATA_QUERY: (metadata),
        github.PROJECT_ITEMS_QUERY: {
            "node": {
                "items": {
                    "nodes": [
                        {
                            **item,
                            "content": issue,
                        },
                        {
                            **item,
                            "id": ("test-item-45"),
                            "content": {
                                **issue,
                                "number": 45,
                                "title": ("[OC63] Outra tarefa de teste"),
                                "body": ("## Branch sugerida\n`feature/test-45`\n"),
                            },
                        },
                    ]
                }
            }
        },
        github.PULL_REQUESTS_QUERY: (pull_request_page(pull_requests)),
    }

    def graphql(
        query,
        variables,
    ):
        assert "mutation" not in query

        return responses[query]

    monkeypatch.setattr(
        github,
        "_graphql",
        graphql,
    )

    contexts = (
        [
            github.get_issue_context(44),
        ]
        if lookup == "single"
        else github.list_project_issues()
    )

    assert [context.issue_number for context in contexts] == (
        [44] if lookup == "single" else [44, 45]
    )

    expected_pr_urls = {
        44: PR_URL if has_pr else None,
        45: None,
    }

    assert all(
        context.pr_url == expected_pr_urls[context.issue_number] for context in contexts
    )

    assert all(context.ci_status is None for context in contexts)

    assert all(context.ci_url is None for context in contexts)


@pytest.mark.parametrize(
    "pr_url",
    [
        PR_URL,
        None,
    ],
)
def test_card_data_and_embed_preserve_optional_pr(
    discord_modules,
    pr_url,
):
    ci_status = "success" if pr_url else None

    ci_url = CI_URL if pr_url else None

    context = issue_context(
        discord_modules,
        pr_url=pr_url,
        ci_status=ci_status,
        ci_url=ci_url,
    )

    data = discord_modules.bot.context_to_card_data(context)

    embed = discord_modules.cards.build_task_embed(data)

    pr_fields = [field for field in embed.fields if (field.name == "🔎 Pull Request")]

    assert isinstance(
        data,
        discord_modules.cards.TaskCardData,
    )

    assert data.pr_url == pr_url
    assert data.ci_status == ci_status
    assert data.ci_url == ci_url

    if pr_url:
        assert len(pr_fields) == 1

        assert pr_fields[0].value == f"[Abrir PR]({pr_url})"

    else:
        assert pr_fields == []


@pytest.mark.parametrize(
    (
        "pr_url",
        "ci_status",
        "expected",
    ),
    [
        (
            None,
            None,
            "⚪ Aguardando PR",
        ),
        (
            PR_URL,
            None,
            "🟡 Aguardando CI",
        ),
        (
            PR_URL,
            "pending",
            "🟡 Em execução",
        ),
        (
            PR_URL,
            "success",
            "🟢 Aprovado",
        ),
        (
            PR_URL,
            "failure",
            "🔴 Falhou",
        ),
    ],
)
def test_card_ci_visuals(
    discord_modules,
    pr_url,
    ci_status,
    expected,
):
    cards = discord_modules.cards

    data = cards.TaskCardData(
        issue_number=44,
        issue_title=("[OC62] Tarefa de teste"),
        issue_url=("https://github.com/example/logistics/issues/44"),
        status="Em revisão",
        responsible=("Pessoa de teste"),
        version="v1.1.0",
        branch="feature/test",
        pr_url=pr_url,
        ci_status=ci_status,
        ci_url=(CI_URL if ci_status else None),
    )

    embed = cards.build_task_embed(data)

    ci_field = next(field for field in embed.fields if field.name == "🧪 CI")

    assert ci_field.value == expected


def test_task_card_view_adds_pr_and_ci_buttons(
    discord_modules,
):
    bot = discord_modules.bot

    context = issue_context(
        discord_modules,
        status="Em revisão",
        pr_url=PR_URL,
        ci_status="success",
        ci_url=CI_URL,
    )

    view = bot.TaskCardView(context)

    buttons = {item.label: item for item in view.children}

    assert "Ver Issue" in buttons

    assert "Ver PR" in buttons

    assert "Ver CI" in buttons

    assert buttons["Ver Issue"].url == context.issue_url

    assert buttons["Ver PR"].url == PR_URL

    assert buttons["Ver CI"].url == CI_URL


def test_dashboard_data_counts_statuses(
    discord_modules,
):
    bot = discord_modules.bot

    contexts = [
        issue_context(
            discord_modules,
            status="Backlog",
        ),
        issue_context(
            discord_modules,
            status=("Pronto para iniciar"),
        ),
        issue_context(
            discord_modules,
            status=("Em desenvolvimento"),
        ),
        issue_context(
            discord_modules,
            status="Em revisão",
        ),
        issue_context(
            discord_modules,
            status="Concluído",
        ),
    ]

    data = bot.contexts_to_dashboard_data(contexts)

    assert data.version == "v1.1.0"
    assert data.total == 5
    assert data.backlog == 1
    assert data.ready == 1
    assert data.development == 1
    assert data.review == 1
    assert data.completed == 1


def test_dashboard_embed_calculates_progress(
    discord_modules,
):
    cards = discord_modules.cards

    data = cards.ProjectDashboardData(
        version="v1.1.0",
        total=10,
        backlog=2,
        ready=2,
        development=2,
        review=1,
        completed=3,
    )

    embed = cards.build_project_dashboard_embed(data)

    assert embed.title == "📦 LOADX • v1.1.0"

    assert "**30% concluído**" in embed.description

    assert any(
        (field.name == "✅ Concluídas" and field.value == "3") for field in embed.fields
    )


def test_new_pr_edits_existing_review_card_without_sending_message(
    discord_modules,
    monkeypatch,
):
    bot = discord_modules.bot

    previous = issue_context(
        discord_modules,
        status="Em revisão",
    )

    updated = issue_context(
        discord_modules,
        status="Em revisão",
        pr_url=PR_URL,
    )

    message = SimpleNamespace(
        embeds=[
            discord_modules.cards.build_task_embed(bot.context_to_card_data(previous))
        ],
        edit=AsyncMock(),
        delete=AsyncMock(),
    )

    channel = SimpleNamespace(
        send=AsyncMock(),
    )

    monkeypatch.setattr(
        bot,
        "list_project_issues",
        lambda: [
            updated,
        ],
    )

    async def synchronize():
        client = bot.LoadXBot()

        try:
            client.cards[44] = message

            client.initialized = True

            monkeypatch.setattr(
                client,
                "get_tasks_channel",
                AsyncMock(return_value=channel),
            )

            completed_channel = SimpleNamespace(
                send=AsyncMock(),
            )

            monkeypatch.setattr(
                client,
                "get_completed_channel",
                AsyncMock(return_value=completed_channel),
            )

            client.completed_initialized = True

            monkeypatch.setattr(
                client,
                "sync_dashboard",
                AsyncMock(),
            )

            await client.sync_cards()

            message.edit.assert_awaited_once()

            embed = message.edit.call_args.kwargs["embed"]

            assert any(
                (field.value == f"[Abrir PR]({PR_URL})") for field in embed.fields
            )

            assert client.cards[44] is message

            message.embeds = [
                embed,
            ]

            await client.sync_cards()

            message.edit.assert_awaited_once()

            message.delete.assert_not_awaited()

            channel.send.assert_not_awaited()

        finally:
            await client.close()

    asyncio.run(synchronize())


def test_completed_issue_is_archived_before_active_card_is_removed(
    discord_modules,
    monkeypatch,
):
    bot = discord_modules.bot

    completed = issue_context(
        discord_modules,
        status="Concluído",
        pr_url=PR_URL,
        pr_number=63,
        pr_merged_at="2026-09-14T19:50:00Z",
        ci_status="success",
        ci_url=CI_URL,
    )

    active_message = SimpleNamespace(
        embeds=[
            discord_modules.cards.build_task_embed(bot.context_to_card_data(completed))
        ],
        edit=AsyncMock(),
        delete=AsyncMock(),
    )

    tasks_channel = SimpleNamespace(
        send=AsyncMock(),
    )

    completed_message = SimpleNamespace(
        embeds=[],
        edit=AsyncMock(),
        delete=AsyncMock(),
    )

    completed_channel = SimpleNamespace(
        send=AsyncMock(return_value=completed_message),
    )

    monkeypatch.setattr(
        bot,
        "list_project_issues",
        lambda: [completed],
    )

    async def synchronize():
        client = bot.LoadXBot()

        try:
            client.cards[44] = active_message
            client.initialized = True
            client.completed_initialized = True

            monkeypatch.setattr(
                client,
                "get_tasks_channel",
                AsyncMock(return_value=tasks_channel),
            )

            monkeypatch.setattr(
                client,
                "get_completed_channel",
                AsyncMock(return_value=completed_channel),
            )

            monkeypatch.setattr(
                client,
                "sync_dashboard",
                AsyncMock(),
            )

            await client.sync_cards()

            completed_channel.send.assert_awaited_once()
            active_message.delete.assert_awaited_once()

            assert 44 not in client.cards
            assert client.completed_cards[44] is completed_message

            embed = completed_channel.send.call_args.kwargs["embed"]

            assert embed.title == ("✅ OC62 • CONCLUÍDA")

            assert any(field.name == "📅 Concluída em" for field in embed.fields)

        finally:
            await client.close()

    asyncio.run(synchronize())


def test_completed_card_can_be_rebuilt_without_active_card(
    discord_modules,
    monkeypatch,
):
    bot = discord_modules.bot

    completed = issue_context(
        discord_modules,
        status="Concluído",
        pr_url=PR_URL,
        pr_number=63,
        issue_closed_at="2026-09-14T20:00:00Z",
        ci_status="success",
        ci_url=CI_URL,
    )

    tasks_channel = SimpleNamespace(
        send=AsyncMock(),
    )

    completed_message = SimpleNamespace(
        embeds=[],
        edit=AsyncMock(),
        delete=AsyncMock(),
    )

    completed_channel = SimpleNamespace(
        send=AsyncMock(return_value=completed_message),
    )

    monkeypatch.setattr(
        bot,
        "list_project_issues",
        lambda: [completed],
    )

    async def synchronize():
        client = bot.LoadXBot()

        try:
            client.initialized = True
            client.completed_initialized = True

            monkeypatch.setattr(
                client,
                "get_tasks_channel",
                AsyncMock(return_value=tasks_channel),
            )

            monkeypatch.setattr(
                client,
                "get_completed_channel",
                AsyncMock(return_value=completed_channel),
            )

            monkeypatch.setattr(
                client,
                "sync_dashboard",
                AsyncMock(),
            )

            await client.sync_cards()

            completed_channel.send.assert_awaited_once()
            tasks_channel.send.assert_not_awaited()

            assert 44 in client.completed_cards

        finally:
            await client.close()

    asyncio.run(synchronize())


def test_completed_card_preserves_pr_merge_metadata(
    discord_modules,
):
    bot = discord_modules.bot
    cards = discord_modules.cards

    context = issue_context(
        discord_modules,
        status="Concluído",
        pr_url=PR_URL,
        pr_number=75,
        pr_merged_at="2026-09-14T19:50:00Z",
        issue_closed_at="2026-09-14T19:51:00Z",
        ci_status="success",
        ci_url=CI_URL,
    )

    data = bot.context_to_completed_card_data(context)
    embed = cards.build_completed_task_embed(data)

    assert data.completed_at == ("2026-09-14T19:50:00Z")

    assert any(
        (field.name == "🔀 Pull Request" and "#75" in field.value)
        for field in embed.fields
    )

    assert any(
        (field.name == "🧪 CI" and field.value == "🟢 Aprovado")
        for field in embed.fields
    )


def test_dashboard_history_button_points_to_completed_channel(
    discord_modules,
):
    bot = discord_modules.bot

    view = bot.ProjectDashboardView()

    button = next(item for item in view.children if item.label == "Ver concluídas")

    assert button.url == ("https://discord.com/channels/996/997")


def test_responsible_discord_ids_ignore_unknown_users(
    discord_modules,
):
    bot = discord_modules.bot

    context = issue_context(
        discord_modules,
        assignees=[
            "RennaN-C",
            "usuario-desconhecido",
            "dacelofe",
        ],
    )

    assert bot.get_responsible_discord_user_ids(context) == {
        2,
        5,
    }


def test_initial_snapshot_does_not_send_release_dm(
    discord_modules,
    monkeypatch,
):
    bot = discord_modules.bot

    ready = issue_context(
        discord_modules,
        status="Pronto para iniciar",
        assignees=[
            "RennaN-C",
        ],
    )

    async def synchronize():
        client = bot.LoadXBot()

        try:
            send_dm = AsyncMock()

            monkeypatch.setattr(
                client,
                "send_released_task_dm",
                send_dm,
            )

            await client.notify_released_tasks([ready])

            send_dm.assert_not_awaited()

            assert client.status_snapshot_initialized is True

            assert client.previous_statuses == {
                44: ("Pronto para iniciar"),
            }

        finally:
            await client.close()

    asyncio.run(synchronize())


def test_backlog_to_ready_sends_one_release_dm(
    discord_modules,
    monkeypatch,
):
    bot = discord_modules.bot

    backlog = issue_context(
        discord_modules,
        status="Backlog",
        assignees=[
            "RennaN-C",
        ],
    )

    ready = issue_context(
        discord_modules,
        status="Pronto para iniciar",
        assignees=[
            "RennaN-C",
        ],
    )

    async def synchronize():
        client = bot.LoadXBot()

        try:
            send_dm = AsyncMock()

            monkeypatch.setattr(
                client,
                "send_released_task_dm",
                send_dm,
            )

            await client.notify_released_tasks([backlog])

            send_dm.assert_not_awaited()

            await client.notify_released_tasks([ready])

            send_dm.assert_awaited_once_with(ready)

            await client.notify_released_tasks([ready])

            send_dm.assert_awaited_once()

            assert client.previous_statuses == {
                44: ("Pronto para iniciar"),
            }

        finally:
            await client.close()

    asyncio.run(synchronize())


def test_non_backlog_transition_does_not_send_release_dm(
    discord_modules,
    monkeypatch,
):
    bot = discord_modules.bot

    development = issue_context(
        discord_modules,
        status="Em desenvolvimento",
        assignees=[
            "RennaN-C",
        ],
    )

    ready = issue_context(
        discord_modules,
        status="Pronto para iniciar",
        assignees=[
            "RennaN-C",
        ],
    )

    async def synchronize():
        client = bot.LoadXBot()

        try:
            send_dm = AsyncMock()

            monkeypatch.setattr(
                client,
                "send_released_task_dm",
                send_dm,
            )

            await client.notify_released_tasks([development])

            await client.notify_released_tasks([ready])

            send_dm.assert_not_awaited()

        finally:
            await client.close()

    asyncio.run(synchronize())


def test_release_dm_goes_to_mapped_responsible_users(
    discord_modules,
    monkeypatch,
):
    bot = discord_modules.bot

    context = issue_context(
        discord_modules,
        status="Pronto para iniciar",
        assignees=[
            "RennaN-C",
            "dacelofe",
            "usuario-desconhecido",
        ],
    )

    renan = SimpleNamespace(
        send=AsyncMock(),
    )

    marcelo = SimpleNamespace(
        send=AsyncMock(),
    )

    users = {
        2: renan,
        5: marcelo,
    }

    async def synchronize():
        client = bot.LoadXBot()

        try:
            monkeypatch.setattr(
                client,
                "get_user",
                lambda user_id: users.get(user_id),
            )

            fetch_user = AsyncMock()

            monkeypatch.setattr(
                client,
                "fetch_user",
                fetch_user,
            )

            await client.send_released_task_dm(context)

            renan.send.assert_awaited_once()

            marcelo.send.assert_awaited_once()

            fetch_user.assert_not_awaited()

            renan_embed = renan.send.call_args.kwargs["embed"]

            assert renan_embed.title == ("🔓 OC LIBERADA • OC62")

            assert "Tarefa de teste" in renan_embed.description

            assert any(
                (field.name == "📌 Status" and field.value == "Pronto para iniciar")
                for field in renan_embed.fields
            )

        finally:
            await client.close()

    asyncio.run(synchronize())


def test_blocked_dm_does_not_break_notification(
    discord_modules,
    monkeypatch,
):
    bot = discord_modules.bot

    context = issue_context(
        discord_modules,
        status="Pronto para iniciar",
        assignees=[
            "RennaN-C",
        ],
    )

    forbidden = discord.Forbidden(
        SimpleNamespace(
            status=403,
            reason="Forbidden",
        ),
        ("Cannot send messages to this user"),
    )

    blocked_user = SimpleNamespace(
        send=AsyncMock(side_effect=forbidden),
    )

    async def synchronize():
        client = bot.LoadXBot()

        try:
            monkeypatch.setattr(
                client,
                "get_user",
                lambda user_id: blocked_user,
            )

            fetch_user = AsyncMock()

            monkeypatch.setattr(
                client,
                "fetch_user",
                fetch_user,
            )

            await client.send_released_task_dm(context)

            blocked_user.send.assert_awaited_once()

            fetch_user.assert_not_awaited()

        finally:
            await client.close()

    asyncio.run(synchronize())


def test_html_comment_closing_reference_is_ignored(
    discord_modules,
):
    body = "<!-- Closes #999 -->\nCloses #44"

    assert discord_modules.github._extract_closing_issue_numbers(body) == {44}


def test_pr_matches_issue_only_with_same_oc_and_branch(
    discord_modules,
):
    github = discord_modules.github

    valid = github.PullRequestInfo(
        url=PR_URL,
        number=63,
        title="[OC62] Tarefa de teste",
        head_ref="feature/test",
    )

    wrong_oc = github.PullRequestInfo(
        url=PR_URL,
        number=63,
        title="[OC63] Outra tarefa",
        head_ref="feature/test",
    )

    wrong_branch = github.PullRequestInfo(
        url=PR_URL,
        number=63,
        title="[OC62] Tarefa de teste",
        head_ref="outra/branch",
    )

    assert github._pull_request_matches_issue(
        valid,
        issue_title="[OC62] Tarefa de teste",
        branch="feature/test",
    )

    assert not github._pull_request_matches_issue(
        wrong_oc,
        issue_title="[OC62] Tarefa de teste",
        branch="feature/test",
    )

    assert not github._pull_request_matches_issue(
        wrong_branch,
        issue_title="[OC62] Tarefa de teste",
        branch="feature/test",
    )


def test_pull_request_with_multiple_issues_is_ignored(
    discord_modules,
    monkeypatch,
):
    github = discord_modules.github

    graphql = Mock(
        return_value=pull_request_page(
            [
                pull_request(
                    "Closes #44\nCloses #45",
                )
            ]
        )
    )

    monkeypatch.setattr(
        github,
        "_graphql",
        graphql,
    )

    assert github._get_pull_request_info() == {}


def test_initial_snapshot_recovers_release_dm_when_card_is_missing(
    discord_modules,
    monkeypatch,
):
    bot = discord_modules.bot

    ready = issue_context(
        discord_modules,
        status="Pronto para iniciar",
        assignees=[
            "RennaN-C",
        ],
    )

    async def synchronize():
        client = bot.LoadXBot()

        try:
            send_dm = AsyncMock()

            monkeypatch.setattr(
                client,
                "send_released_task_dm",
                send_dm,
            )

            await client.notify_released_tasks(
                [ready],
                known_card_issue_numbers=set(),
            )

            send_dm.assert_awaited_once_with(ready)

            await client.notify_released_tasks(
                [ready],
                known_card_issue_numbers=set(),
            )

            send_dm.assert_awaited_once()

            assert client.status_snapshot_initialized is True

        finally:
            await client.close()

    asyncio.run(synchronize())


def test_initial_snapshot_does_not_repeat_dm_when_card_already_exists(
    discord_modules,
    monkeypatch,
):
    bot = discord_modules.bot

    ready = issue_context(
        discord_modules,
        status="Pronto para iniciar",
        assignees=[
            "RennaN-C",
        ],
    )

    async def synchronize():
        client = bot.LoadXBot()

        try:
            send_dm = AsyncMock()

            monkeypatch.setattr(
                client,
                "send_released_task_dm",
                send_dm,
            )

            await client.notify_released_tasks(
                [ready],
                known_card_issue_numbers={44},
            )

            send_dm.assert_not_awaited()

            assert client.status_snapshot_initialized is True

        finally:
            await client.close()

    asyncio.run(synchronize())
