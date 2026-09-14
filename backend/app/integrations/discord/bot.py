import asyncio
import re

import discord
from discord.ext import tasks
from discord.ui import Button, View

from app.integrations.discord.cards import (
    ProjectDashboardData,
    TaskCardData,
    build_project_dashboard_embed,
    build_task_embed,
)
from app.integrations.discord.config import settings
from app.integrations.discord.github_client import (
    IssueProjectContext,
    get_issue_context,
    list_project_issues,
    update_issue_status,
)

ACTIVE_STATUSES = {
    "Pronto para iniciar",
    "Em desenvolvimento",
    "Em revisão",
}

ISSUE_FOOTER_PATTERN = re.compile(r"Issue #(\d+)")

ISSUE_URL_PATTERN = re.compile(r"/issues/(\d+)/?$")

TEAM_DISCORD_IDS = {
    "RennaN-C": settings.discord_rennan_user_id,
    "joao-victor-weber": settings.discord_joao_user_id,
    "marlon-myszka": settings.discord_marlon_user_id,
    "dacelofe": settings.discord_marcelo_user_id,
}

DASHBOARD_FOOTER_TEXT = "LoadX • Dashboard atualizado automaticamente"


def contexts_to_dashboard_data(
    contexts: list[IssueProjectContext],
) -> ProjectDashboardData:
    return ProjectDashboardData(
        version=settings.github_target_milestone,
        total=len(contexts),
        backlog=sum(context.current_status == "Backlog" for context in contexts),
        ready=sum(
            context.current_status == "Pronto para iniciar" for context in contexts
        ),
        development=sum(
            context.current_status == "Em desenvolvimento" for context in contexts
        ),
        review=sum(context.current_status == "Em revisão" for context in contexts),
        completed=sum(context.current_status == "Concluído" for context in contexts),
    )


def get_authorized_user_ids(
    context: IssueProjectContext,
) -> set[int]:
    authorized = {
        settings.discord_owner_user_id,
    }

    for github_login in context.assignees:
        discord_user_id = TEAM_DISCORD_IDS.get(github_login)

        if discord_user_id:
            authorized.add(discord_user_id)

    return authorized


def get_responsible_discord_user_ids(
    context: IssueProjectContext,
) -> set[int]:
    user_ids: set[int] = set()

    for github_login in context.assignees:
        discord_user_id = TEAM_DISCORD_IDS.get(github_login)

        if discord_user_id:
            user_ids.add(discord_user_id)

    return user_ids


def context_to_card_data(
    context: IssueProjectContext,
) -> TaskCardData:
    return TaskCardData(
        issue_number=context.issue_number,
        issue_title=context.issue_title,
        issue_url=context.issue_url,
        status=context.current_status,
        responsible=context.responsible,
        version=context.version,
        branch=context.branch,
        pr_url=context.pr_url,
    )


def issue_number_from_message(
    message: discord.Message,
) -> int | None:
    for embed in message.embeds:
        footer_text = embed.footer.text if embed.footer else None

        if footer_text:
            match = ISSUE_FOOTER_PATTERN.search(footer_text)

            if match:
                return int(match.group(1))

        if embed.url:
            match = ISSUE_URL_PATTERN.search(embed.url)

            if match:
                return int(match.group(1))

    return None


def build_released_task_dm_embed(
    context: IssueProjectContext,
) -> discord.Embed:
    title = context.issue_title.strip()

    if title.startswith("[") and "]" in title:
        oc_code = title[1 : title.index("]")].strip()

        task_title = title.split(
            "]",
            1,
        )[1].strip()

    else:
        oc_code = f"ISSUE #{context.issue_number}"
        task_title = title

    embed = discord.Embed(
        title=f"🔓 OC LIBERADA • {oc_code}",
        description=(
            f"### {task_title}\n\n"
            "Todas as dependências foram concluídas "
            "e esta tarefa já pode ser iniciada."
        ),
        color=discord.Color.green(),
        url=context.issue_url,
    )

    embed.add_field(
        name="📦 Versão",
        value=context.version,
        inline=True,
    )

    embed.add_field(
        name="📌 Status",
        value="Pronto para iniciar",
        inline=True,
    )

    embed.add_field(
        name="🔗 Issue",
        value=(f"[#{context.issue_number} • Abrir no GitHub]({context.issue_url})"),
        inline=False,
    )

    embed.set_footer(text=("LoadX • Sua próxima tarefa está disponível"))

    return embed


class StartTaskButton(Button):
    def __init__(
        self,
        issue_number: int,
    ) -> None:
        super().__init__(
            label="Iniciar OC",
            emoji="▶️",
            style=discord.ButtonStyle.success,
            custom_id=(f"loadx:issue:{issue_number}:start"),
        )

        self.issue_number = issue_number

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await interaction.response.defer(
            ephemeral=True,
            thinking=True,
        )

        try:
            current = await asyncio.to_thread(
                get_issue_context,
                self.issue_number,
            )

            authorized_users = get_authorized_user_ids(current)

            if interaction.user.id not in authorized_users:
                await interaction.followup.send(
                    "⛔ Você não pode iniciar "
                    "esta OC.\n\n"
                    "Responsável: "
                    f"**{current.responsible}**",
                    ephemeral=True,
                )

                return

            if current.current_status != "Pronto para iniciar":
                if interaction.message:
                    await interaction.message.edit(
                        embed=build_task_embed(context_to_card_data(current)),
                        view=TaskCardView(current),
                    )

                await interaction.followup.send(
                    "ℹ️ Esta OC não está mais em "
                    "**Pronto para iniciar**.\n\n"
                    "Status atual no GitHub: "
                    f"**{current.current_status}**",
                    ephemeral=True,
                )

                return

            updated = await asyncio.to_thread(
                update_issue_status,
                self.issue_number,
                "Em desenvolvimento",
            )

            if interaction.message:
                await interaction.message.edit(
                    embed=build_task_embed(context_to_card_data(updated)),
                    view=TaskCardView(updated),
                )

            await interaction.followup.send(
                "✅ **OC iniciada com sucesso.**\n\n"
                "GitHub Project → "
                "**Em desenvolvimento**\n"
                "Card do Discord → atualizado",
                ephemeral=True,
            )

        except (
            RuntimeError,
            discord.DiscordException,
            OSError,
        ) as exc:
            await interaction.followup.send(
                f"❌ Não foi possível iniciar a OC.\n\n`{exc}`",
                ephemeral=True,
            )


class TaskCardView(View):
    def __init__(
        self,
        context: IssueProjectContext,
    ) -> None:
        super().__init__(timeout=None)

        if context.current_status == "Pronto para iniciar":
            self.add_item(StartTaskButton(context.issue_number))

        elif context.current_status == "Em desenvolvimento":
            started_button = Button(
                label="OC iniciada",
                emoji="🟡",
                style=discord.ButtonStyle.secondary,
                disabled=True,
                custom_id=(f"loadx:issue:{context.issue_number}:started"),
            )

            self.add_item(started_button)

        self.add_item(
            Button(
                label="Ver Issue",
                emoji="🔗",
                style=discord.ButtonStyle.link,
                url=context.issue_url,
            )
        )


class LoadXBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.none()
        intents.guilds = True

        super().__init__(intents=intents)

        self.cards: dict[
            int,
            discord.Message,
        ] = {}

        self.initialized = False
        self.sync_lock = asyncio.Lock()

        self.dashboard_message: discord.Message | None = None

        self.previous_statuses: dict[
            int,
            str | None,
        ] = {}

        self.status_snapshot_initialized = False

    async def setup_hook(self) -> None:
        try:
            contexts = await asyncio.to_thread(list_project_issues)

            for context in contexts:
                self.add_view(TaskCardView(context))

            print(f"Views persistentes registradas: {len(contexts)}")

        except (
            RuntimeError,
            discord.DiscordException,
            OSError,
        ) as exc:
            print(f"ERRO ao registrar views: {exc}")

        self.sync_loop.start()

    async def on_ready(self) -> None:
        print(f"Bot conectado: {self.user}")

    async def get_tasks_channel(
        self,
    ) -> discord.TextChannel:
        channel = self.get_channel(settings.discord_tasks_channel_id)

        if channel is None:
            channel = await self.fetch_channel(settings.discord_tasks_channel_id)

        if not isinstance(
            channel,
            discord.TextChannel,
        ):
            raise TypeError("O canal configurado não é um canal de texto.")

        return channel

    async def get_status_channel(
        self,
    ) -> discord.TextChannel:
        channel = self.get_channel(settings.discord_status_channel_id)

        if channel is None:
            channel = await self.fetch_channel(settings.discord_status_channel_id)

        if not isinstance(
            channel,
            discord.TextChannel,
        ):
            raise TypeError("O canal de status configurado não é um canal de texto.")

        return channel

    async def discover_dashboard_message(
        self,
        channel: discord.TextChannel,
    ) -> None:
        if self.user is None:
            return

        async for message in channel.history(limit=50):
            if message.author.id != self.user.id:
                continue

            for embed in message.embeds:
                footer_text = embed.footer.text if embed.footer else None

                if footer_text == DASHBOARD_FOOTER_TEXT:
                    self.dashboard_message = message

                    print("Dashboard existente encontrado.")

                    return

    async def sync_dashboard(
        self,
        contexts: list[IssueProjectContext],
    ) -> None:
        channel = await self.get_status_channel()

        if self.dashboard_message is None:
            await self.discover_dashboard_message(channel)

        embed = build_project_dashboard_embed(contexts_to_dashboard_data(contexts))

        if self.dashboard_message is not None:
            try:
                await self.dashboard_message.edit(
                    embed=embed,
                )

                print("Dashboard atualizado.")

                return

            except discord.NotFound:
                self.dashboard_message = None

        self.dashboard_message = await channel.send(
            embed=embed,
        )

        print("Dashboard criado.")

    async def discover_existing_cards(
        self,
        channel: discord.TextChannel,
    ) -> None:
        if self.user is None:
            return

        self.cards.clear()

        async for message in channel.history(limit=200):
            if message.author.id != self.user.id:
                continue

            issue_number = issue_number_from_message(message)

            if issue_number is None:
                continue

            self.cards[issue_number] = message

        print(f"Cards existentes encontrados: {len(self.cards)}")

    async def create_card(
        self,
        channel: discord.TextChannel,
        context: IssueProjectContext,
    ) -> None:
        message = await channel.send(
            embed=build_task_embed(context_to_card_data(context)),
            view=TaskCardView(context),
        )

        self.cards[context.issue_number] = message

        print(f"Card criado: Issue #{context.issue_number}")

    async def update_card(
        self,
        context: IssueProjectContext,
        message: discord.Message,
    ) -> None:
        new_embed = build_task_embed(context_to_card_data(context))

        current_embed = message.embeds[0] if message.embeds else None

        needs_update = (
            current_embed is None or current_embed.to_dict() != new_embed.to_dict()
        )

        if not needs_update:
            return

        await message.edit(
            embed=new_embed,
            view=TaskCardView(context),
        )

        print(
            f"Card atualizado: Issue #{context.issue_number} → {context.current_status}"
        )

    async def send_released_task_dm(
        self,
        context: IssueProjectContext,
    ) -> None:
        responsible_user_ids = get_responsible_discord_user_ids(context)

        if not responsible_user_ids:
            print(
                "DM não enviada: "
                f"Issue #{context.issue_number} "
                "não possui responsável "
                "mapeado no Discord."
            )

            return

        embed = build_released_task_dm_embed(context)

        for user_id in responsible_user_ids:
            try:
                user = self.get_user(user_id)

                if user is None:
                    user = await self.fetch_user(user_id)

                await user.send(embed=embed)

                print(
                    "DM de OC liberada enviada: "
                    f"Issue #{context.issue_number} "
                    f"→ Discord User {user_id}"
                )

            except discord.Forbidden:
                print(
                    "DM ignorada: usuário "
                    f"{user_id} bloqueou ou "
                    "não aceita mensagens privadas. "
                    f"Issue #{context.issue_number}"
                )

            except discord.DiscordException as exc:
                print(
                    "ERRO ao enviar DM da "
                    f"Issue #{context.issue_number} "
                    f"para {user_id}: {exc}"
                )

    async def notify_released_tasks(
        self,
        contexts: list[IssueProjectContext],
    ) -> None:
        current_statuses = {
            context.issue_number: context.current_status for context in contexts
        }

        if not self.status_snapshot_initialized:
            self.previous_statuses = current_statuses

            self.status_snapshot_initialized = True

            print("Snapshot inicial de status registrado.")

            return

        for context in contexts:
            previous_status = self.previous_statuses.get(context.issue_number)

            if (
                previous_status == "Backlog"
                and context.current_status == "Pronto para iniciar"
            ):
                await self.send_released_task_dm(context)

        self.previous_statuses = current_statuses

    async def sync_cards(
        self,
    ) -> None:
        async with self.sync_lock:
            channel = await self.get_tasks_channel()

            if not self.initialized:
                await self.discover_existing_cards(channel)

                self.initialized = True

            contexts = await asyncio.to_thread(list_project_issues)

            try:
                await self.sync_dashboard(contexts)

            except (
                RuntimeError,
                TypeError,
                discord.DiscordException,
                OSError,
            ) as exc:
                print(f"ERRO ao sincronizar dashboard: {exc}")

            for context in contexts:
                issue_number = context.issue_number

                status = context.current_status

                existing = self.cards.get(issue_number)

                if status == "Backlog":
                    if existing:
                        try:
                            await existing.delete()

                        except discord.NotFound:
                            pass

                        self.cards.pop(
                            issue_number,
                            None,
                        )

                        print(
                            "Card removido por "
                            "retorno ao Backlog: "
                            f"Issue #{issue_number}"
                        )

                    continue

                if status == "Concluído":
                    if existing:
                        try:
                            await existing.delete()

                        except discord.NotFound:
                            pass

                        self.cards.pop(
                            issue_number,
                            None,
                        )

                        print(f"Card removido por conclusão: Issue #{issue_number}")

                    continue

                if status not in ACTIVE_STATUSES:
                    continue

                if existing:
                    try:
                        await self.update_card(
                            context,
                            existing,
                        )

                    except discord.NotFound:
                        self.cards.pop(
                            issue_number,
                            None,
                        )

                        await self.create_card(
                            channel,
                            context,
                        )

                else:
                    await self.create_card(
                        channel,
                        context,
                    )

            await self.notify_released_tasks(contexts)

            print("Sincronização concluída.")

    @tasks.loop(seconds=60)
    async def sync_loop(
        self,
    ) -> None:
        try:
            await self.sync_cards()

        except (
            RuntimeError,
            discord.DiscordException,
            OSError,
        ) as exc:
            print(f"ERRO na sincronização: {exc}")

    @sync_loop.before_loop
    async def before_sync_loop(
        self,
    ) -> None:
        await self.wait_until_ready()


def main() -> None:
    client = LoadXBot()

    client.run(settings.discord_bot_token)


if __name__ == "__main__":
    main()
