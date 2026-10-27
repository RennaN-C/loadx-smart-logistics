"""Fixed HTTPS Groq endpoint, bounded bodies, no redirects/retries/raw logging."""

import json
import logging
import ssl
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from app.core.config import Settings
from app.integrations.ai.provider import (
    AIExplanationContext,
    AIProviderOutput,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)

ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
MAX_BODY_BYTES = 65_536
logger = logging.getLogger(__name__)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AIProviderUnavailableError


class GroqProvider:
    def __init__(self, config: Settings) -> None:
        self.config = config

    def complete(
        self,
        messages: list[dict],
        *,
        tools: list[dict] | None = None,
        timeout_seconds: float,
    ) -> dict:
        key = self.config.groq_api_key
        if (
            self.config.ai_provider != "groq"
            or key is None
            or not key.get_secret_value().strip()
        ):
            raise AIProviderUnavailableError
        payload = {
            "model": self.config.groq_model,
            "messages": messages,
            "temperature": 0,
            "max_completion_tokens": 2048,
        }
        if tools:
            payload.update(tools=tools, tool_choice="auto", parallel_tool_calls=False)
        encoded = json.dumps(payload).encode()
        if len(encoded) > MAX_BODY_BYTES:
            raise AIProviderUnavailableError
        request = Request(
            ENDPOINT,
            data=encoded,
            headers={
                "Authorization": "Bearer " + key.get_secret_value(),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        opener = build_opener(_NoRedirect(), HTTPSHandler(context=context))
        try:
            with opener.open(request, timeout=timeout_seconds) as response:
                body = response.read(MAX_BODY_BYTES + 1)
            if len(body) > MAX_BODY_BYTES:
                raise AIProviderUnavailableError
            return self._parse_response(body)
        except HTTPError as error:
            # Log only an HTTP status; provider bodies can contain private prompts.
            status = (
                error.code
                if error.code in {400, 401, 403, 404, 413, 422, 429, 498, 500, 502, 503}
                else "other"
            )
            logger.warning("GROQ_REQUEST_FAILURE category=http_%s", status)
            raise AIProviderUnavailableError from None
        except TimeoutError:
            logger.warning("GROQ_REQUEST_FAILURE category=timeout")
            raise AIProviderTimeoutError from None
        except (
            OSError,
            ValueError,
            KeyError,
            IndexError,
            TypeError,
            RecursionError,
        ):
            logger.warning("GROQ_REQUEST_FAILURE category=transport_or_payload")
            raise AIProviderUnavailableError from None

    @staticmethod
    def _parse_response(body: bytes) -> dict:
        result = json.loads(body)["choices"][0]["message"]
        if not isinstance(result, dict) or result.get("role") != "assistant":
            raise AIProviderUnavailableError
        content = result.get("content")
        calls = result.get("tool_calls", [])
        if content is not None and (
            not isinstance(content, str) or len(content) > 8000
        ):
            raise AIProviderUnavailableError
        if not isinstance(calls, list) or len(calls) > 3:
            raise AIProviderUnavailableError
        if not content and not calls:
            raise AIProviderUnavailableError
        # Do not forward provider metadata or arbitrary message fields.
        return {
            "role": "assistant",
            "content": content,
            **({"tool_calls": calls} if calls else {}),
        }

    def explain_load_plan(
        self, context: AIExplanationContext, *, timeout_seconds: float
    ) -> object:
        summary = context.model_dump(
            mode="json", exclude={"placed_volumes", "rejected_volumes"}
        )
        result = self.complete(
            [
                {
                    "role": "system",
                    "content": "Você é o Assistente LoadX. Explique somente os fatos técnicos fornecidos em português. Não recalcule nem aprove a carga. Não invente capacidade ou resultados.",
                },
                {"role": "user", "content": json.dumps(summary)},
            ],
            timeout_seconds=timeout_seconds,
        )
        if result.get("tool_calls"):
            raise AIProviderUnavailableError
        return AIProviderOutput(explanation=result["content"])


class UnconfiguredAIProvider:
    def explain_load_plan(
        self, context: AIExplanationContext, *, timeout_seconds: float
    ) -> object:
        raise AIProviderUnavailableError
