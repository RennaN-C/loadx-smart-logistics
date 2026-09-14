import asyncio
import re

import discord
from discord.ext import tasks
from discord.ui import Button, View

from app.integrations.discord.cards import (
    TaskCardData,
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

ISSUE_FOOTER_PATTERN = re.compile(
    r"Issue #(\d+)"
)

ISSUE_URL_PATTERN = re.compile(
    r"/issues/(\d+)/?$"
)

TEAM_DISCORD_IDS = {
    "RennaN-C": settings.discord_rennan_user_id,
    "joao-victor-weber": settings.discord_joao_user_id,
    "marlon-myszka": settings.discord_marlon_user_id,
    "dacelofe": settings.discord_marcelo_user_id,
}


def get_authorized_user_ids(
    context: IssueProjectContext,
) -> set[int]:
    authorized = {
        settings.discord_owner_user_id,
    }

    for github_login in context.assignees:
        discord_user_id = TEAM_DISCORD_IDS.get(
            github_login
        )

        if discord_user_id:
            authorized.add(discord_user_id)

    return authorized


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
    )


def issue_number_from_message(
    message: discord.Message,
) -> int | None:
    for embed in message.embeds:
        footer_text = (
            embed.footer.text
            if embed.footer
            else None
        )

        if footer_text:
            match = ISSUE_FOOTER_PATTERN.search(
                footer_text
            )

            if match:
                return int(match.group(1))

        if embed.url:
            match = ISSUE_URL_PATTERN.search(
                embed.url
            )

            if match:
                return int(match.group(1))

    return None


class StartTaskButton(Button):
    def __init__(
        self,
        issue_number: int,
    ) -> None:
        super().__init__(
            label="Iniciar OC",
            emoji="▶️",
            style=discord.ButtonStyle.success,
            custom_id=(
                f"loadx:issue:"
                f"{issue_number}:start"
            ),
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

            authorized_users = (
                get_authorized_user_ids(current)
            )

            if (
                interaction.user.id
                not in authorized_users
            ):
                await interaction.followup.send(
                    "⛔ Você não pode iniciar "
                    "esta OC.\n\n"
                    "Responsável: "
                    f"**{current.responsible}**",
                    ephemeral=True,
                )
                return

            if (
                current.current_status
                != "Pronto para iniciar"
            ):
                if interaction.message:
                    await interaction.message.edit(
                        embed=build_task_embed(
                            context_to_card_data(
                                current
                            )
                        ),
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
                    embed=build_task_embed(
                        context_to_card_data(
                            updated
                        )
                    ),
                    view=TaskCardView(updated),
                )

            await interaction.followup.send(
                "✅ **OC iniciada com sucesso.**\n\n"
                "GitHub Project → "
                "**Em desenvolvimento**\n"
                "Card do Discord → atualizado",
                ephemeral=True,
            )

        except Exception as exc:
            await interaction.followup.send(
                "❌ Não foi possível iniciar "
                "a OC.\n\n"
                f"`{exc}`",
                ephemeral=True,
            )


class TaskCardView(View):
    def __init__(
        self,
        context: IssueProjectContext,
    ) -> None:
        super().__init__(
            timeout=None
        )

        if (
            context.current_status
            == "Pronto para iniciar"
        ):
            self.add_item(
                StartTaskButton(
                    context.issue_number
                )
            )

        elif (
            context.current_status
            == "Em desenvolvimento"
        ):
            started_button = Button(
                label="OC iniciada",
                emoji="🟡",
                style=(
                    discord.ButtonStyle.secondary
                ),
                disabled=True,
                custom_id=(
                    f"loadx:issue:"
                    f"{context.issue_number}:started"
                ),
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

        super().__init__(
            intents=intents
        )

        self.cards: dict[
            int,
            discord.Message,
        ] = {}

        self.initialized = False
        self.sync_lock = asyncio.Lock()

    async def setup_hook(self) -> None:
        try:
            contexts = await asyncio.to_thread(
                list_project_issues
            )

            for context in contexts:
                self.add_view(
                    TaskCardView(context)
                )

            print(
                "Views persistentes registradas: "
                f"{len(contexts)}"
            )

        except Exception as exc:
            print(
                "ERRO ao registrar views: "
                f"{exc}"
            )

        self.sync_loop.start()

    async def on_ready(self) -> None:
        print(
            f"Bot conectado: {self.user}"
        )

    async def get_tasks_channel(
        self,
    ) -> discord.TextChannel:
        channel = self.get_channel(
            settings.discord_tasks_channel_id
        )

        if channel is None:
            channel = await self.fetch_channel(
                settings.discord_tasks_channel_id
            )

        if not isinstance(
            channel,
            discord.TextChannel,
        ):
            raise RuntimeError(
                "O canal configurado "
                "não é um canal de texto."
            )

        return channel

    async def discover_existing_cards(
        self,
        channel: discord.TextChannel,
    ) -> None:
        if self.user is None:
            return

        self.cards.clear()

        async for message in channel.history(
            limit=200
        ):
            if (
                message.author.id
                != self.user.id
            ):
                continue

            issue_number = (
                issue_number_from_message(
                    message
                )
            )

            if issue_number is None:
                continue

            self.cards[issue_number] = (
                message
            )

        print(
            "Cards existentes encontrados: "
            f"{len(self.cards)}"
        )

    async def create_card(
        self,
        channel: discord.TextChannel,
        context: IssueProjectContext,
    ) -> None:
        message = await channel.send(
            embed=build_task_embed(
                context_to_card_data(
                    context
                )
            ),
            view=TaskCardView(context),
        )

        self.cards[
            context.issue_number
        ] = message

        print(
            f"Card criado: "
            f"Issue #{context.issue_number}"
        )

    async def update_card(
        self,
        context: IssueProjectContext,
        message: discord.Message,
    ) -> None:
        new_embed = build_task_embed(
            context_to_card_data(
                context
            )
        )

        current_embed = (
            message.embeds[0]
            if message.embeds
            else None
        )

        needs_update = (
            current_embed is None
            or current_embed.to_dict()
            != new_embed.to_dict()
        )

        if not needs_update:
            return

        await message.edit(
            embed=new_embed,
            view=TaskCardView(context),
        )

        print(
            f"Card atualizado: "
            f"Issue #{context.issue_number} "
            f"→ {context.current_status}"
        )

    async def sync_cards(
        self,
    ) -> None:
        async with self.sync_lock:
            channel = (
                await self.get_tasks_channel()
            )

            if not self.initialized:
                await self.discover_existing_cards(
                    channel
                )

                self.initialized = True

            contexts = await asyncio.to_thread(
                list_project_issues
            )

            for context in contexts:
                issue_number = (
                    context.issue_number
                )

                status = (
                    context.current_status
                )

                existing = self.cards.get(
                    issue_number
                )

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
                            await self.update_card(
                                context,
                                existing,
                            )
                        except discord.NotFound:
                            self.cards.pop(
                                issue_number,
                                None,
                            )

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

            print(
                "Sincronização concluída."
            )

    @tasks.loop(
        seconds=60
    )
    async def sync_loop(self) -> None:
        try:
            await self.sync_cards()

        except Exception as exc:
            print(
                "ERRO na sincronização: "
                f"{exc}"
            )

    @sync_loop.before_loop
    async def before_sync_loop(
        self,
    ) -> None:
        await self.wait_until_ready()


def main() -> None:
    client = LoadXBot()

    client.run(
        settings.discord_bot_token
    )


if __name__ == "__main__":
    main()
