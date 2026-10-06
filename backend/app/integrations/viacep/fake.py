from dataclasses import dataclass

from app.integrations.viacep.provider import (
    ViaCEPAddress,
    ViaCEPProviderError,
    normalize_cep,
    validate_timeout_seconds,
    validate_viacep_output,
)


@dataclass(frozen=True, slots=True)
class ViaCEPProviderCall:
    cep: str
    timeout_seconds: float


_DEFAULT_FAKE_RESPONSE = object()


class FakeViaCEPProvider:
    """Fake observável, com dados fictícios e o mesmo contrato validado do adapter."""

    def __init__(
        self,
        *,
        response: object = _DEFAULT_FAKE_RESPONSE,
        error: ViaCEPProviderError | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.calls: list[ViaCEPProviderCall] = []

    def lookup_address(self, cep: str, *, timeout_seconds: float) -> ViaCEPAddress:
        cep = normalize_cep(cep)
        timeout = validate_timeout_seconds(timeout_seconds)
        self.calls.append(ViaCEPProviderCall(cep=cep, timeout_seconds=timeout))
        if self.error is not None:
            raise self.error
        response = self.response
        if response is _DEFAULT_FAKE_RESPONSE:
            response = {
                "cep": cep,
                "street": "Rua Fictícia",
                "neighborhood": "Bairro Fictício",
                "complement": None,
                "city": "Cidade Fictícia",
                "state": "SP",
            }
        return validate_viacep_output(response, requested_cep=cep)
