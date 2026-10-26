import hashlib
import hmac
import uuid

import pytest
from pydantic import SecretBytes

from app.integrations.external_commands import (
    BoundExternalActorResolver,
    HmacExternalAuthenticator,
    TrustedIntegration,
)
from app.modules.external_commands.errors import ExternalCommandError
from app.modules.external_commands.schemas import CommandName

KEY = bytes(range(32))  # Deterministic fixture, never a configured credential.


def test_authenticity_returns_only_server_configured_identity_and_capabilities():
    trusted = TrustedIntegration("fixture", frozenset({CommandName.START_TRIP}))
    authenticator = HmacExternalAuthenticator(trusted, SecretBytes(KEY))
    body = b'{"role":"ADMIN","integration_id":"spoofed"}'
    signature = hmac.new(KEY, body, hashlib.sha256).hexdigest()
    assert authenticator.authenticate(body, signature) is trusted
    assert KEY.hex() not in repr(authenticator)
    assert repr(KEY) not in repr(authenticator)


@pytest.mark.parametrize("signature", ("", "x" * 64, "0" * 64, None))
def test_invalid_signature_is_predictable_and_does_not_echo_it(signature):
    authenticator = HmacExternalAuthenticator(
        TrustedIntegration("fixture", frozenset()), SecretBytes(KEY)
    )
    with pytest.raises(ExternalCommandError, match="^EXTERNAL_AUTHENTICITY_INVALID$"):
        authenticator.authenticate(b"sensitive-body", signature)


def test_signature_binds_every_body_byte_and_cannot_cross_integrations():
    trusted = TrustedIntegration("fixture", frozenset())
    authenticator = HmacExternalAuthenticator(trusted, SecretBytes(KEY))
    signed = hmac.new(KEY, b"original", hashlib.sha256).hexdigest()
    with pytest.raises(ExternalCommandError):
        authenticator.authenticate(b"changed", signed)
    other = HmacExternalAuthenticator(trusted, SecretBytes(bytes(reversed(KEY))))
    with pytest.raises(ExternalCommandError):
        other.authenticate(b"original", signed)


def test_identity_requires_a_server_binding_scoped_to_the_integration():
    actor = uuid.uuid4()
    bindings = {("fixture", "subject"): actor}
    resolver = BoundExternalActorResolver(bindings)
    bindings[("fixture", "subject")] = uuid.uuid4()
    trusted = TrustedIntegration("fixture", frozenset())
    assert resolver.resolve(trusted, "subject") == actor
    for integration, subject in (
        (trusted, str(actor)),
        (trusted, "unknown"),
        (TrustedIntegration("other", frozenset()), "subject"),
    ):
        with pytest.raises(ExternalCommandError, match="^EXTERNAL_COMMAND_FORBIDDEN$"):
            resolver.resolve(integration, subject)


def test_invalid_server_configuration_fails_closed():
    with pytest.raises(ValueError):
        TrustedIntegration("invalid integration", frozenset())
    with pytest.raises(ValueError):
        TrustedIntegration("fixture", frozenset({"unknown"}))
    with pytest.raises(ValueError):
        HmacExternalAuthenticator(
            TrustedIntegration("fixture", frozenset()), SecretBytes(b"short")
        )
    with pytest.raises(ValueError):
        BoundExternalActorResolver({("fixture", "subject"): "not-a-uuid"})
