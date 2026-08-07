from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.modules.auth.bootstrap import run_bootstrap
from app.modules.auth.service import AuthService
from app.modules.users.models import User

SessionFactory = Callable[[], Session]


def test_run_bootstrap_creates_admin_without_exposing_password(
    session_factory: SessionFactory,
) -> None:
    text_answers = iter(["Admin Inicial", "ADMIN@EXAMPLE.TEST"])
    password_answers = iter(["senha-local", "senha-local"])
    messages: list[str] = []

    exit_code = run_bootstrap(
        session_factory=session_factory,
        read_text=lambda _prompt: next(text_answers),
        read_password=lambda _prompt: next(password_answers),
        write=messages.append,
    )

    with session_factory() as db:
        user = db.scalar(select(User))

    assert exit_code == 0
    assert user is not None
    assert user.role == "ADMIN"
    assert user.active is True
    assert verify_password("senha-local", user.password_hash) is True
    assert "senha-local" not in " ".join(messages)


def test_run_bootstrap_rejects_password_confirmation_mismatch() -> None:
    text_answers = iter(["Admin Inicial", "admin@example.test"])
    password_answers = iter(["senha-local", "senha-diferente"])
    messages: list[str] = []

    def unexpected_session() -> Session:
        raise AssertionError("database must not be accessed")

    exit_code = run_bootstrap(
        session_factory=unexpected_session,
        read_text=lambda _prompt: next(text_answers),
        read_password=lambda _prompt: next(password_answers),
        write=messages.append,
    )

    assert exit_code == 1
    assert messages[-1] == (
        "Não foi possível criar o administrador: as senhas não coincidem."
    )


def test_run_bootstrap_refuses_database_with_existing_user(
    session_factory: SessionFactory,
) -> None:
    with session_factory() as db:
        AuthService(db).bootstrap_first_admin(
            name="Admin Existente",
            email="admin@example.test",
            password="senha-local",
        )

    text_answers = iter(["Outro Admin", "outro@example.test"])
    password_answers = iter(["outra-senha", "outra-senha"])
    messages: list[str] = []

    exit_code = run_bootstrap(
        session_factory=session_factory,
        read_text=lambda _prompt: next(text_answers),
        read_password=lambda _prompt: next(password_answers),
        write=messages.append,
    )

    with session_factory() as db:
        users = db.scalars(select(User)).all()

    assert exit_code == 1
    assert len(users) == 1
    assert messages[-1] == "Bootstrap recusado: o banco já possui usuário cadastrado."
