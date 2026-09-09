import pytest

from app.core.exceptions import ApiError
from app.modules.auth.dependencies import require_roles
from app.modules.users.models import User


def make_user(role: str) -> User:
    return User(
        name="Usuário de Teste",
        email=f"{role.lower()}@example.test",
        password_hash="not-a-real-hash",
        role=role,
        active=True,
    )


def test_require_roles_returns_user_with_allowed_role() -> None:
    user = make_user("ADMIN")
    role_dependency = require_roles("ADMIN", "LOGISTICS_MANAGER")

    current_user = role_dependency(user)

    assert current_user is user


def test_require_roles_rejects_user_without_allowed_role() -> None:
    role_dependency = require_roles("ADMIN")

    with pytest.raises(ApiError) as error_info:
        role_dependency(make_user("CHECKER"))

    assert error_info.value.status_code == 403
    assert error_info.value.code == "AUTH_FORBIDDEN"
    assert error_info.value.message == "Usuário sem permissão para esta ação."


@pytest.mark.parametrize("roles", [(), ("UNKNOWN",)])
def test_require_roles_rejects_invalid_configuration(roles: tuple[str, ...]) -> None:
    with pytest.raises(ValueError):
        require_roles(*roles)
