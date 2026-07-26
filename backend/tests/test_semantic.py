from __future__ import annotations

from app.services import qa
from tests.conftest import requires_db


def test_vector_literal_formats_pgvector_input():
    assert qa._vector_literal([1.0, 2.5, -0.3]) == "[1.0,2.5,-0.3]"
    assert qa._vector_literal([]) == "[]"


@requires_db
def test_pgvector_inactive_falls_back_on_dev_db(db_session):
    # The test DB is built from the model (JSONB only) with no `vector`
    # extension, so detection must report inactive and never raise.
    qa.reset_pgvector_detection()
    assert qa.pgvector_active(db_session) is False


@requires_db
def test_pgvector_disabled_by_setting(db_session, monkeypatch):
    from app.core.config import Settings, get_settings

    get_settings.cache_clear()
    qa.reset_pgvector_detection()
    disabled = Settings(_env_file=None, pgvector_enabled=False)
    monkeypatch.setattr(qa, "get_settings", lambda: disabled)
    assert qa.pgvector_active(db_session) is False
    get_settings.cache_clear()
