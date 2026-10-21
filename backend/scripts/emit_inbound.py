"""Local OC83 emitter: preserve event bytes across retries; never print secrets."""

import argparse
import hashlib
import hmac
import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

ERROR_CODES = frozenset(
    {
        "EXTERNAL_AUTHENTICITY_INVALID",
        "EXTERNAL_PAYLOAD_INVALID",
        "EXTERNAL_COMMAND_EXPIRED",
        "EXTERNAL_COMMAND_NOT_YET_VALID",
        "EXTERNAL_COMMAND_FORBIDDEN",
        "EXTERNAL_IDENTITY_CONFLICT",
        "EXTERNAL_DOMAIN_REJECTED",
        "EXTERNAL_PROCESSING_FAILED",
        "INBOUND_HEADERS_INVALID",
        "INBOUND_REQUEST_INCOMPLETE",
        "INBOUND_BODY_TIMEOUT",
        "INBOUND_BODY_TOO_LARGE",
        "INBOUND_CONTENT_TYPE_INVALID",
        "INBOUND_BUSY",
        "INBOUND_NOT_CONFIGURED",
    }
)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def event_bytes(args, parser: argparse.ArgumentParser) -> bytes:
    if not args.event_file.exists():
        if not all((args.subject, args.command, args.target_id)):
            parser.error("A new event file requires subject, command and target-id.")
        now = datetime.now(UTC)
        payload = {
            "version": 1,
            "event_id": uuid.uuid4().hex,
            "subject": args.subject,
            "command": args.command,
            "target_id": str(args.target_id),
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=4)).isoformat(),
        }
        with args.event_file.open("xb") as output:
            output.write(json.dumps(payload, separators=(",", ":")).encode())
        args.event_file.chmod(0o600)
    with args.event_file.open("rb") as source:
        body = source.read(16 * 1024 + 1)
    if not 0 < len(body) <= 16 * 1024:
        parser.error("Event must contain 1 to 16384 bytes.")
    return body


def public_result(status: int, body: bytes) -> dict:
    result = json.loads(body)
    if status >= 400:
        code = result["code"]
        if code not in ERROR_CODES:
            raise ValueError("unknown error code")
        return {"http_status": status, "code": code}
    receipt_id = str(uuid.UUID(result["id"]))
    duplicate = result["duplicate"]
    if type(duplicate) is not bool:
        raise ValueError("invalid result")
    return {"http_status": status, "id": receipt_id, "duplicate": duplicate}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-file", type=Path, required=True)
    parser.add_argument("--subject")
    parser.add_argument(
        "--command", choices=("START_TRIP", "START_DELIVERY", "FINISH_DELIVERY")
    )
    parser.add_argument("--target-id", type=uuid.UUID)
    parser.add_argument("--invalid-signature", action="store_true")
    parser.add_argument("--expected-status", type=int, default=200)
    args = parser.parse_args()
    key = os.environ.get("INBOUND_WEBHOOK_SIGNING_KEY", "").encode()
    if len(key) < 32:
        parser.error("Set a local exclusive signing key in the secure environment.")
    body = event_bytes(args, parser)
    signature = hmac.new(key, body, hashlib.sha256).hexdigest()
    if args.invalid_signature:
        signature = ("0" if signature[0] != "0" else "1") + signature[1:]
    request = Request(
        "http://127.0.0.1:8000/api/v1/webhooks/controlled-events",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "X-LoadX-Signature": signature},
    )
    try:
        response = build_opener(NoRedirect()).open(request, timeout=15)
    except HTTPError as error:
        response = error
    except URLError:
        print("HTTP transport unavailable; event preserved for explicit retry.")
        return 1
    with response:
        status = response.code
        validated = False
        # Only publish contract-shaped technical results, never an arbitrary response.
        try:
            published = public_result(status, response.read(4096))
            validated = True
            print(json.dumps(published))
        except (ValueError, KeyError, TypeError):
            print(json.dumps({"http_status": status}))
    return 0 if status == args.expected_status and validated else 1


if __name__ == "__main__":
    raise SystemExit(main())
