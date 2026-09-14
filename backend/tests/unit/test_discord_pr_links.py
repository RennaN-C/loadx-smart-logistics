import asyncio
import importlib
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import discord
import pytest

PR_URL = "https://github.com/example/logistics/pull/63"


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
        discord_status_channel_id=999,
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
    updated_at="2026-09-13T12:00:00Z",
):
    return {
        "body": body,
        "baseRefName": base,
        "url": url,
        "updatedAt": updated_at,
    }


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
                    "hasNextPage": cursor is not None,
                    "endCursor": cursor,
                },
            }
        }
    }


def issue_context(
    discord_modules,
    *,
    pr_url=None,
    status="Em revisão",
    assignees=None,
):
    if assignees is None:
        assignees = ["test-user"]

    return discord_modules.github.IssueProjectContext(
        issue_number=44,
        issue_title="[OC62] Tarefa de teste",
        issue_url="https://github.com/example/logistics/issues/44",
        issue_state="OPEN",
        issue_body="",
        responsible="Pessoa de teste",
        version="v1.1.0",
        branch="feature/test",
        assignees=assignees,
        project_id="test-project",
        project_item_id="test-item",
        status_field_id="test-status-field",
        current_status=status,
        status_options={},
        pr_url=pr_url,
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

    assert discord_modules.github._extract_closing_issue_numbers(body) == {46, 47, 48}


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
                pull_request("Closes #44\nCloses #45"),
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
        45: PR_URL,
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
                        "Fixes #44\nResolves #45",
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
        45: latest_url,
    }

    assert [call.args[1]["cursor"] for call in graphql.call_args_list] == [
        None,
        "next-page",
    ]

    assert "after: $cursor" in github.PULL_REQUESTS_QUERY


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
                    "id": "test-status-field",
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
        "title": "[OC62] Tarefa de teste",
        "url": ("https://github.com/example/logistics/issues/44"),
        "state": "OPEN",
        "body": "",
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

    responses = {
        github.PROJECT_ISSUE_QUERY: {
            **metadata,
            "repository": {
                "issue": issue,
            },
        },
        github.PROJECT_METADATA_QUERY: metadata,
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
                            "id": "test-item-45",
                            "content": {
                                **issue,
                                "number": 45,
                            },
                        },
                    ]
                }
            }
        },
        github.PULL_REQUESTS_QUERY: (
            pull_request_page(
                [pull_request("Closes #44\nCloses #45")] if has_pr else []
            )
        ),
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

    assert all(context.pr_url == (PR_URL if has_pr else None) for context in contexts)


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
    context = issue_context(
        discord_modules,
        pr_url=pr_url,
    )

    data = discord_modules.bot.context_to_card_data(context)

    embed = discord_modules.cards.build_task_embed(data)

    fields = [field for field in embed.fields if field.name == "🔎 Pull Request"]

    assert isinstance(
        data,
        discord_modules.cards.TaskCardData,
    )

    assert data.pr_url == pr_url

    if pr_url:
        assert len(fields) == 1

        assert fields[0].value == f"[Abrir PR]({pr_url})"

    else:
        assert fields == []


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
            status="Pronto para iniciar",
        ),
        issue_context(
            discord_modules,
            status="Em desenvolvimento",
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
        field.name == "✅ Concluídas" and field.value == "3" for field in embed.fields
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
        lambda: [updated],
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

            monkeypatch.setattr(
                client,
                "sync_dashboard",
                AsyncMock(),
            )

            await client.sync_cards()

            message.edit.assert_awaited_once()

            embed = message.edit.call_args.kwargs["embed"]

            assert any(field.value == f"[Abrir PR]({PR_URL})" for field in embed.fields)

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


def test_completed_issue_removes_existing_card(
    discord_modules,
    monkeypatch,
):
    bot = discord_modules.bot

    completed = issue_context(
        discord_modules,
        status="Concluído",
        pr_url=PR_URL,
    )

    message = SimpleNamespace(
        embeds=[
            discord_modules.cards.build_task_embed(bot.context_to_card_data(completed))
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
        lambda: [completed],
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

            monkeypatch.setattr(
                client,
                "sync_dashboard",
                AsyncMock(),
            )

            await client.sync_cards()

            message.delete.assert_awaited_once()
            message.edit.assert_not_awaited()

            assert 44 not in client.cards

            channel.send.assert_not_awaited()

        finally:
            await client.close()

    asyncio.run(synchronize())


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
        assignees=["RennaN-C"],
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
                44: "Pronto para iniciar",
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
        assignees=["RennaN-C"],
    )

    ready = issue_context(
        discord_modules,
        status="Pronto para iniciar",
        assignees=["RennaN-C"],
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
                44: "Pronto para iniciar",
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
        assignees=["RennaN-C"],
    )

    ready = issue_context(
        discord_modules,
        status="Pronto para iniciar",
        assignees=["RennaN-C"],
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

            assert renan_embed.title == "🔓 OC LIBERADA • OC62"

            assert "Tarefa de teste" in renan_embed.description

            assert any(
                field.name == "📌 Status" and field.value == "Pronto para iniciar"
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
        assignees=["RennaN-C"],
    )

    forbidden = discord.Forbidden(
        SimpleNamespace(
            status=403,
            reason="Forbidden",
        ),
        "Cannot send messages to this user",
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
