import pytest

from app.database import session


class FakeSession:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_get_db_closes_session(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session = FakeSession()
    monkeypatch.setattr(session, "SessionLocal", lambda: fake_session)

    db_generator = session.get_db()

    assert next(db_generator) is fake_session
    with pytest.raises(StopIteration):
        next(db_generator)
    assert fake_session.closed is True
