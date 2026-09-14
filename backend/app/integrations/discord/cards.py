from dataclasses import dataclass

import discord


@dataclass(frozen=True)
class TaskCardData:
    issue_number: int
    issue_title: str
    issue_url: str
    status: str | None

    responsible: str = "Não atribuído"
    version: str = "Não informada"
    branch: str | None = None
    pr_url: str | None = None


@dataclass(frozen=True)
class ProjectDashboardData:
    version: str
    total: int
    backlog: int
    ready: int
    development: int
    review: int
    completed: int


STATUS_VISUALS = {
    "Pronto para iniciar": {
        "emoji": "🟢",
        "label": "PRONTA PARA INICIAR",
        "color": discord.Color.green(),
    },
    "Em desenvolvimento": {
        "emoji": "🟡",
        "label": "EM DESENVOLVIMENTO",
        "color": discord.Color.yellow(),
    },
    "Em revisão": {
        "emoji": "🔵",
        "label": "EM REVISÃO",
        "color": discord.Color.blue(),
    },
    "Concluído": {
        "emoji": "✅",
        "label": "CONCLUÍDA",
        "color": discord.Color.green(),
    },
}


def extract_oc_code(issue_title: str) -> str:
    title = issue_title.strip()

    if title.startswith("[") and "]" in title:
        return title[1 : title.index("]")].strip()

    return "OC"


def extract_task_title(issue_title: str) -> str:
    title = issue_title.strip()

    if title.startswith("[") and "]" in title:
        return title.split("]", 1)[1].strip()

    return title


def build_task_embed(
    data: TaskCardData,
) -> discord.Embed:
    visual = STATUS_VISUALS.get(
        data.status,
        {
            "emoji": "⚪",
            "label": (data.status.upper() if data.status else "SEM STATUS"),
            "color": discord.Color.light_grey(),
        },
    )

    oc_code = extract_oc_code(data.issue_title)

    task_title = extract_task_title(data.issue_title)

    embed = discord.Embed(
        title=(f"{visual['emoji']} {oc_code} • {visual['label']}"),
        description=f"### {task_title}",
        color=visual["color"],
        url=data.issue_url,
    )

    embed.add_field(
        name="👤 Responsável",
        value=data.responsible,
        inline=True,
    )

    embed.add_field(
        name="📌 Status",
        value=data.status or "Sem status",
        inline=True,
    )

    embed.add_field(
        name="📦 Versão",
        value=data.version,
        inline=True,
    )

    embed.add_field(
        name="🔗 Issue",
        value=(f"[#{data.issue_number} • Abrir no GitHub]({data.issue_url})"),
        inline=False,
    )

    if data.branch:
        embed.add_field(
            name="🌿 Branch",
            value=f"`{data.branch}`",
            inline=False,
        )

    if data.pr_url:
        embed.add_field(
            name="🔎 Pull Request",
            value=f"[Abrir PR]({data.pr_url})",
            inline=False,
        )

    embed.set_footer(text=(f"LoadX • Desenvolvimento • Issue #{data.issue_number}"))

    return embed


def build_project_dashboard_embed(
    data: ProjectDashboardData,
) -> discord.Embed:
    progress = round((data.completed / data.total) * 100) if data.total else 0

    filled_blocks = round(progress / 10)
    progress_bar = "█" * filled_blocks + "░" * (10 - filled_blocks)

    embed = discord.Embed(
        title=f"📦 LOADX • {data.version}",
        description=(
            f"### Status do projeto\n`{progress_bar}` **{progress}% concluído**"
        ),
        color=discord.Color.blue(),
    )

    embed.add_field(
        name="✅ Concluídas",
        value=str(data.completed),
        inline=True,
    )

    embed.add_field(
        name="🔵 Em revisão",
        value=str(data.review),
        inline=True,
    )

    embed.add_field(
        name="🟡 Em desenvolvimento",
        value=str(data.development),
        inline=True,
    )

    embed.add_field(
        name="🟢 Prontas para iniciar",
        value=str(data.ready),
        inline=True,
    )

    embed.add_field(
        name="🔒 Backlog / bloqueadas",
        value=str(data.backlog),
        inline=True,
    )

    embed.add_field(
        name="📋 Total de OCs",
        value=str(data.total),
        inline=True,
    )

    embed.set_footer(
        text="LoadX • Dashboard atualizado automaticamente",
    )

    embed.timestamp = discord.utils.utcnow()

    return embed
