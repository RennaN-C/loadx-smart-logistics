from sqlalchemy.exc import IntegrityError


def get_integrity_constraint_name(error: IntegrityError) -> str | None:
    """Return the PostgreSQL constraint name reported by psycopg, when available."""
    diagnostics = getattr(error.orig, "diag", None)
    constraint_name = getattr(diagnostics, "constraint_name", None)
    if isinstance(constraint_name, str) and constraint_name:
        return constraint_name
    return None
