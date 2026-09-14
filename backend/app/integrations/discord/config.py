from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[4]


class DiscordBotSettings(BaseSettings):
    # Discord
    discord_bot_token: str
    discord_tasks_channel_id: int
    discord_guild_id: int

    # Usuário com permissão administrativa no bot.
    # Depois adicionaremos os IDs dos responsáveis de cada OC.
    discord_owner_user_id: int

    # Desenvolvedores
    discord_rennan_user_id: int
    discord_joao_user_id: int
    discord_marlon_user_id: int
    discord_marcelo_user_id: int

    # GitHub
    github_token: str

    github_owner: str = "RennaN-C"
    github_repository: str = "loadx-smart-logistics"

    github_project_title: str = "LoadX — Desenvolvimento"
    github_status_field: str = "Status"
    github_target_milestone: str = "v1.1.0"

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env.discord",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = DiscordBotSettings()