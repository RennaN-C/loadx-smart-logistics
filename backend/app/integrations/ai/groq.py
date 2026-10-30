"""Fixed HTTPS Groq endpoint, bounded bodies, no redirects/retries/raw logging."""

import json
import logging
import ssl
import time
from threading import Lock
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
# A identificacao padrao Python-urllib e bloqueada por alguns filtros da borda da Groq.
USER_AGENT = "LoadX-Smart-Logistics/1.2"
logger = logging.getLogger(__name__)

# Process-local short circuit for repeated Groq 429s. Backend facts continue
# without a provider; do not retry blindly or log provider response bodies.
_rate_lock = Lock()
_rate_limited_until = 0.0


class AIProviderToolGenerationError(AIProviderUnavailableError):
    """Groq rejected malformed model-generated tool calls; no tool was executed."""


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
        if self.config.app_env != "local":
            with _rate_lock:
                if time.monotonic() < _rate_limited_until:
                    raise AIProviderUnavailableError("http_429")
        payload = {
            "model": self.config.groq_model,
            "messages": messages,
            "temperature": 0.35,
            "max_completion_tokens": 2048,
        }
        if tools:
            payload.update(tools=tools, tool_choice="auto", parallel_tool_calls=False)
        elif (
            messages
            and isinstance(messages[0], dict)
            and isinstance(messages[0].get("content"), str)
            and "Você é o Loxi, assistente operacional do LoadX"
            in messages[0]["content"]
        ):
            # JSON mode only for the Loxi conversational contract. The separate
            # technical explanation endpoint still expects ordinary prose.
            payload["response_format"] = {"type": "json_object"}
        if self.config.groq_model.startswith("openai/gpt-oss-") and (
            tools or "response_format" in payload
        ):
            # Groq requires parsed/hidden reasoning with JSON mode/tool calling.
            payload["reasoning_format"] = "hidden"
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
                "User-Agent": USER_AGENT,
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
            self._raise_http_error(error)
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
    def _invalid_tool_generation(error: HTTPError) -> bool:
        # Read a bounded body and only match the structured indicator.
        try:
            details = json.loads(error.read(4096))
        except (OSError, ValueError, TypeError):
            return False
        issue = details.get("error") if isinstance(details, dict) else None
        return bool(
            isinstance(issue, dict)
            and "failed_generation" in issue
            and isinstance(issue["failed_generation"], (dict, str))
        )

    @staticmethod
    def _forbidden_reason(error: HTTPError) -> str:
        # Never log arbitrary messages, prompts or authentication data.
        try:
            body = error.read(4096)
            if b"error code: 1010" in body.lower():
                return "edge_client_signature_1010"
            details = json.loads(body)
        except (OSError, ValueError, TypeError):
            return "unclassified"
        if not isinstance(details, dict):
            return "unclassified"
        metadata = details.get("error")
        if not isinstance(metadata, dict):
            return "unclassified"
        code = metadata.get("code")
        if code in {
            "model_permission_blocked_org",
            "model_permission_blocked_project",
        }:
            return code
        return "unclassified"

    def _raise_http_error(self, error: HTTPError) -> None:
        global _rate_limited_until
        status = (
            error.code
            if error.code in {400, 401, 403, 404, 413, 422, 429, 498, 500, 502, 503}
            else "other"
        )
        if status == 429 and self.config.app_env != "local":
            with _rate_lock:
                _rate_limited_until = max(
                    _rate_limited_until, time.monotonic() + 60
                )
        if status == 400 and self._invalid_tool_generation(error):
            logger.warning(
                "GROQ_REQUEST_FAILURE category=http_400 "
                "reason=invalid_tool_generation"
            )
            raise AIProviderToolGenerationError from None
        if status == 403:
            logger.warning(
                "GROQ_REQUEST_FAILURE category=http_403 reason=%s",
                self._forbidden_reason(error),
            )
        else:
            logger.warning("GROQ_REQUEST_FAILURE category=http_%s", status)
        raise AIProviderUnavailableError(f"http_{status}") from None

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
