import pytest

from app.core.config import settings
from app.core.exceptions import ApiError
from app.integrations.evidence_storage import LocalEvidenceStorage
from app.modules.deliveries.evidence_router import get_evidence_storage


def test_storage_is_opt_in_and_never_enabled_in_production(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "evidence_storage_dir", None)
    monkeypatch.setattr(settings, "app_env", "local")
    with pytest.raises(ApiError) as missing:
        get_evidence_storage()
    assert missing.value.status_code == 503
    root = tmp_path / "private"
    monkeypatch.setattr(settings, "evidence_storage_dir", root)
    assert isinstance(get_evidence_storage(), LocalEvidenceStorage)
    monkeypatch.setattr(settings, "app_env", "production")
    with pytest.raises(ApiError) as denied:
        get_evidence_storage()
    assert denied.value.code == "EVIDENCE_STORAGE_UNAVAILABLE"


def test_storage_configuration_failure_does_not_disclose_path(monkeypatch, tmp_path):
    root = tmp_path / "private-provider-path"
    root.mkdir()
    root.chmod(0o755)
    monkeypatch.setattr(settings, "app_env", "local")
    monkeypatch.setattr(settings, "evidence_storage_dir", root)
    with pytest.raises(ApiError) as caught:
        get_evidence_storage()
    assert caught.value.status_code == 503
    assert str(root) not in str(caught.value)
