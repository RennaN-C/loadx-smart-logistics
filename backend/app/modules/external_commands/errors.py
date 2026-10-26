from enum import StrEnum


class ExternalCommandErrorCode(StrEnum):
    AUTHENTICITY_INVALID = "EXTERNAL_AUTHENTICITY_INVALID"
    PAYLOAD_INVALID = "EXTERNAL_PAYLOAD_INVALID"
    EXPIRED = "EXTERNAL_COMMAND_EXPIRED"
    NOT_YET_VALID = "EXTERNAL_COMMAND_NOT_YET_VALID"
    FORBIDDEN = "EXTERNAL_COMMAND_FORBIDDEN"
    IDENTITY_CONFLICT = "EXTERNAL_IDENTITY_CONFLICT"
    DOMAIN_REJECTED = "EXTERNAL_DOMAIN_REJECTED"
    PROCESSING_FAILED = "EXTERNAL_PROCESSING_FAILED"


class ExternalCommandError(Exception):
    def __init__(self, code: ExternalCommandErrorCode) -> None:
        self.code = code
        super().__init__(code.value)
