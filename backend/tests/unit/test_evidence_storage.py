import base64
import uuid
from io import BytesIO

import pytest
from PIL import Image

from app.integrations.evidence_storage import (
    EvidenceStorageError,
    FakeEvidenceStorage,
    LocalEvidenceStorage,
)
from app.modules.deliveries.evidence_content import (
    EvidenceContentInvalidError,
    validate_evidence_content,
)
from app.modules.deliveries.evidence_schemas import MAX_EVIDENCE_BYTES


def image_base64(format: str = "PNG", color: str = "red") -> str:
    output = BytesIO()
    Image.new("RGB", (4, 4), color).save(output, format=format)
    return base64.b64encode(output.getvalue()).decode()


@pytest.mark.parametrize("format,mime", (("PNG", "image/png"), ("JPEG", "image/jpeg")))
def test_content_detects_format_and_removes_hidden_trailers(format, mime):
    source = base64.b64decode(image_base64(format)) + b"private-token-hidden-metadata"
    content = validate_evidence_content(base64.b64encode(source).decode())
    assert content.media_type == mime
    assert b"private-token" not in content.data
    with Image.open(BytesIO(content.data)) as image:
        image.verify()


@pytest.mark.parametrize(
    "source",
    (
        "not base64",
        "",
        base64.b64encode(b"<html>attack</html>").decode(),
        image_base64("GIF"),
    ),
)
def test_unsupported_or_invalid_content_is_rejected(source):
    with pytest.raises(EvidenceContentInvalidError):
        validate_evidence_content(source)


def test_limits_and_truncated_image_are_rejected():
    for source in (
        b"x" * (MAX_EVIDENCE_BYTES + 1),
        base64.b64decode(image_base64())[:16],
    ):
        with pytest.raises(EvidenceContentInvalidError):
            validate_evidence_content(base64.b64encode(source).decode())


@pytest.mark.parametrize("local", (False, True))
def test_adapters_share_immutable_opaque_key_contract(tmp_path, local):
    storage = (
        LocalEvidenceStorage(tmp_path / "private") if local else FakeEvidenceStorage()
    )
    key = uuid.uuid4()
    storage.put(key, b"image-data")
    assert storage.read(key) == b"image-data"
    with pytest.raises(EvidenceStorageError):
        storage.put(key, b"overwrite")
    assert storage.read(key) == b"image-data"
    storage.discard(key)
    storage.discard(key)
    with pytest.raises(EvidenceStorageError):
        storage.read(key)


def test_local_adapter_rejects_client_path_symlink_and_public_root(tmp_path):
    root = tmp_path / "private"
    storage = LocalEvidenceStorage(root)
    with pytest.raises(EvidenceStorageError):
        storage.read("../../outside")
    outside = tmp_path / "outside"
    outside.write_bytes(b"secret")
    key = uuid.uuid4()
    (root / f"{key.hex}.bin").symlink_to(outside)
    with pytest.raises(EvidenceStorageError):
        storage.read(key)
    assert outside.read_bytes() == b"secret"
    link = tmp_path / "root-link"
    link.symlink_to(root, target_is_directory=True)
    with pytest.raises(EvidenceStorageError):
        LocalEvidenceStorage(link)
    public = tmp_path / "public"
    public.mkdir(mode=0o755)
    public.chmod(0o755)
    with pytest.raises(EvidenceStorageError):
        LocalEvidenceStorage(public)


def test_local_adapter_bounds_reads(tmp_path):
    storage = LocalEvidenceStorage(tmp_path / "private")
    key = uuid.uuid4()
    storage.put(key, b"x" * (MAX_EVIDENCE_BYTES + 1))
    with pytest.raises(EvidenceStorageError):
        storage.read(key)
