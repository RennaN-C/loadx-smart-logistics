from collections.abc import Callable
from getpass import getpass

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.modules.auth.service import (
    AuthBootstrapAlreadyCompletedError,
    AuthService,
)

SessionFactory = Callable[[], Session]
TextReader = Callable[[str], str]
TextWriter = Callable[[str], None]


def _validation_fields(error: ValidationError) -> str:
    fields = {".".join(str(part) for part in item["loc"]) for item in error.errors()}
    return ", ".join(sorted(fields))


def run_bootstrap(
    session_factory: SessionFactory = SessionLocal,
    read_text: TextReader = input,
    read_password: TextReader = getpass,
    write: TextWriter = print,
) -> int:
    write("Criação segura do primeiro administrador do LoadX.")
    name = read_text("Nome: ")
    email = read_text("E-mail: ")
    password = read_password("Senha: ")
    password_confirmation = read_password("Confirme a senha: ")

    if password != password_confirmation:
        write("Não foi possível criar o administrador: as senhas não coincidem.")
        return 1

    try:
        with session_factory() as db:
            AuthService(db).bootstrap_first_admin(name, email, password)
    except AuthBootstrapAlreadyCompletedError:
        write("Bootstrap recusado: o banco já possui usuário cadastrado.")
        return 1
    except ValidationError as error:
        fields = _validation_fields(error)
        write(f"Não foi possível criar o administrador. Campos inválidos: {fields}.")
        return 1
    except SQLAlchemyError:
        write("Não foi possível criar o administrador por uma falha no banco.")
        return 1

    write("Primeiro administrador criado com sucesso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_bootstrap())
