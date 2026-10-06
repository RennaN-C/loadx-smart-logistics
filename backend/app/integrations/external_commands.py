"""Vendor-neutral authenticity/identity ports; configured by trusted server code."""

import hashlib
import hmac
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Protocol

from pydantic import SecretBytes

from app.modules.external_commands.errors import (
    ExternalCommandError,
    ExternalCommandErrorCode,
)
from app.modules.external_commands.schemas import CommandName


@dataclass(frozen=True, slots=True)
class TrustedIntegration:
    integration_id: str
    capabilities: frozenset[CommandName]

    def __post_init__(self) -> None:
        if re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", self.integration_id) is None:
            raise ValueError("invalid configured integration identity")
        if not isinstance(self.capabilities, frozenset) or not self.capabilities <= set(
            CommandName
        ):
            raise ValueError("invalid configured integration capabilities")


class ExternalAuthenticator(Protocol):
    def authenticate(self, body: bytes, signature: str) -> TrustedIntegration:
        """Verify original bytes; never derive capabilities from client claims."""


class ExternalActorResolver(Protocol):
    def resolve(self, integration: TrustedIntegration, subject: str) -> uuid.UUID:
        """Return a server-bound actor, not an arbitrary client user_id/role."""


@dataclass(frozen=True, slots=True)
class HmacExternalAuthenticator:
    integration: TrustedIntegration
    key: SecretBytes = field(repr=False)

    def __post_init__(self) -> None:
        if len(self.key.get_secret_value()) < 32:
            raise ValueError("integration signing key requires at least 32 bytes")

    def authenticate(self, body: bytes, signature: str) -> TrustedIntegration:
        expected = hmac.new(
            self.key.get_secret_value(), body, hashlib.sha256
        ).hexdigest()
        if (
            not isinstance(signature, str)
            or re.fullmatch(r"[0-9a-f]{64}", signature) is None
        ):
            raise ExternalCommandError(ExternalCommandErrorCode.AUTHENTICITY_INVALID)
        if not hmac.compare_digest(expected, signature):
            raise ExternalCommandError(ExternalCommandErrorCode.AUTHENTICITY_INVALID)
        return self.integration


class BoundExternalActorResolver:
    def __init__(self, bindings: Mapping[tuple[str, str], uuid.UUID]) -> None:
        if any(not isinstance(value, uuid.UUID) for value in bindings.values()):
            raise ValueError("actor bindings require UUID values")
        self._bindings = MappingProxyType(dict(bindings))

    def resolve(self, integration: TrustedIntegration, subject: str) -> uuid.UUID:
        actor_id = self._bindings.get((integration.integration_id, subject))
        if actor_id is None:
            raise ExternalCommandError(ExternalCommandErrorCode.FORBIDDEN)
        return actor_id
