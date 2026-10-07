import base64
import binascii
import hashlib
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, UnidentifiedImageError

from app.modules.deliveries.evidence_schemas import MAX_EVIDENCE_BYTES


class EvidenceContentInvalidError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ValidatedEvidenceContent:
    data: bytes
    media_type: str
    source_hash: str


def validate_evidence_content(content_base64: str) -> ValidatedEvidenceContent:
    """Decode, verify and re-encode pixels without EXIF, text or hidden trailers."""
    try:
        source = base64.b64decode(content_base64, validate=True)
        if not 0 < len(source) <= MAX_EVIDENCE_BYTES:
            raise EvidenceContentInvalidError
        with Image.open(BytesIO(source)) as image:
            detected = image.format
            if (
                detected not in {"PNG", "JPEG"}
                or image.width * image.height > 20_000_000
                or getattr(image, "n_frames", 1) != 1
            ):
                raise EvidenceContentInvalidError
            image.verify()
        with Image.open(BytesIO(source)) as image:
            image.load()
            converted = image.convert(
                "RGBA" if detected == "PNG" and "A" in image.getbands() else "RGB"
            )
            # Copy pixels to an image with no inherited metadata (including ICC).
            clean = Image.frombytes(converted.mode, converted.size, converted.tobytes())
            output = BytesIO()
            clean.save(output, format=detected)
        data = output.getvalue()
        if len(data) > MAX_EVIDENCE_BYTES:
            raise EvidenceContentInvalidError
        return ValidatedEvidenceContent(
            data,
            "image/png" if detected == "PNG" else "image/jpeg",
            hashlib.sha256(source).hexdigest(),
        )
    except (
        ValueError,
        binascii.Error,
        OSError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
    ):
        raise EvidenceContentInvalidError from None
