"""Branded recovery messages stay safe and usable in text-only mail clients."""

from html import escape

from app.integrations.password_recovery.message import build_recovery_message


def test_recovery_email_has_branded_sender_and_two_mime_parts():
    message = build_recovery_message(
        "client@example.test",
        "test-token",
        "loadx@example.test",
        "https://example.test/password-reset",
    )
    assert message.is_multipart()
    assert message["Subject"] == "LoadX | Redefinição de senha"
    assert "LoadX | Segurança" in str(message["From"])
    assert message["To"] == "client@example.test"

    plain = message.get_body(preferencelist=("plain",)).get_content()
    html = message.get_body(preferencelist=("html",)).get_content()
    link = "https://example.test/password-reset#token=test-token"
    assert link in plain
    assert f'href="{link}"' in html
    assert "Redefinir minha senha" in html
    assert "LoadX" in html
    assert "15 minutos" in plain and "15 minutos" in html
    assert "códigos do autenticador" in plain
    assert "códigos do autenticador" in html
    assert not any(item in html for item in ("<script", "<img", "fonts.google"))
    assert "test-token" not in str(message.items())


def test_recovery_email_escapes_html_url_and_preserves_plaintext_link():
    url = "https://example.test/reset?next=<other>&mode=a"
    message = build_recovery_message(
        "client@example.test", "fake-token", "loadx@example.test", url
    )
    plain = message.get_body(preferencelist=("plain",)).get_content()
    html = message.get_body(preferencelist=("html",)).get_content()
    link = f"{url}#token=fake-token"
    assert link in plain
    assert escape(link, quote=True) in html
    assert link not in html
