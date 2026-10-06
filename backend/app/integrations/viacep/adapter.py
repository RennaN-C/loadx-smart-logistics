import httpx2

from app.integrations.viacep.provider import (
    ViaCEPAddress,
    ViaCEPInvalidResponseError,
    ViaCEPNotFoundError,
    ViaCEPTimeoutError,
    ViaCEPUnavailableError,
    normalize_cep,
    validate_timeout_seconds,
    validate_viacep_output,
)


class HTTPViaCEPProvider:
    """Adapter síncrono: envia somente CEP e nunca compartilha sessão de cliente."""

    def __init__(self, *, transport: httpx2.BaseTransport | None = None) -> None:
        self._transport = transport

    def lookup_address(self, cep: str, *, timeout_seconds: float) -> ViaCEPAddress:
        cep = normalize_cep(cep)
        timeout = validate_timeout_seconds(timeout_seconds)
        try:
            with httpx2.Client(transport=self._transport, trust_env=False) as client:
                response = client.get(
                    f"https://viacep.com.br/ws/{cep}/json/",
                    timeout=httpx2.Timeout(timeout),
                    follow_redirects=False,
                    headers={"Accept": "application/json"},
                )
        except httpx2.TimeoutException:
            raise ViaCEPTimeoutError() from None
        except httpx2.DecodingError:
            raise ViaCEPInvalidResponseError() from None
        except httpx2.RequestError:
            raise ViaCEPUnavailableError() from None

        if response.status_code != 200:
            raise ViaCEPUnavailableError()
        try:
            payload = response.json()
        except (ValueError, UnicodeError):
            raise ViaCEPInvalidResponseError() from None
        if not isinstance(payload, dict):
            raise ViaCEPInvalidResponseError()
        if "erro" in payload:
            if payload["erro"] is True or payload["erro"] == "true":
                raise ViaCEPNotFoundError()
            raise ViaCEPInvalidResponseError()

        return validate_viacep_output(
            {
                "cep": payload.get("cep"),
                "street": payload.get("logradouro"),
                "neighborhood": payload.get("bairro"),
                "complement": payload.get("complemento"),
                "city": payload.get("localidade"),
                "state": payload.get("uf"),
            },
            requested_cep=cep,
        )
