from __future__ import annotations

import os

# Disable abuse rate limiting before any app module (and its cached settings)
# is imported, so repeated requests across the suite never trip the limiter.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
# Don't spin up the background digest scheduler during tests.
os.environ.setdefault("SCHEDULER_ENABLED", "false")

from collections.abc import Iterator  # noqa: E402

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (register models on Base.metadata)
from app.db.base import Base

TEST_DB_URL = os.getenv(
    "VARIORUM_TEST_DATABASE_URL",
    "postgresql+psycopg://variorum:variorum@localhost:5432/variorum_test",
)


def _db_available() -> bool:
    try:
        engine = create_engine(TEST_DB_URL)
        with engine.connect() as conn:
            conn.execute(text("select 1"))
        engine.dispose()
        return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(), reason="test database not reachable (see conftest.TEST_DB_URL)"
)


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    eng = create_engine(TEST_DB_URL)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    """A session wrapped in an outer transaction that is always rolled back, so
    each test is isolated even though services call commit() (savepoints)."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def sample_repo(tmp_path):
    """A small working tree: Python + JS source, docs, and an ignored dir."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "import os\n"
        "from typing import Any\n\n"
        "class Widget:\n"
        "    def render(self, ctx: Any):\n"
        "        return ctx\n\n"
        "def helper():\n"
        "    return 1\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "util.js").write_text(
        "import x from 'y';\n"
        "export function doThing() { return 1; }\n"
        "class Thing {}\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "# Sample Project\n\n"
        "The `Widget` class lives in `src/app.py`. See also doThing.\n",
        encoding="utf-8",
    )
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "ignored.py").write_text(
        "def nope():\n    pass\n", encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def client(db_session: Session):
    from fastapi.testclient import TestClient

    from app.api.deps import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def authed_client(db_session: Session):
    """A TestClient with a seeded user injected as the current user."""
    from fastapi.testclient import TestClient

    from app.api.deps import get_current_user, get_db, get_optional_user
    from app.main import app
    from app.models import User

    user = User(email="tester@example.com", name="Tester", github_user_id=999999)
    db_session.add(user)
    db_session.flush()

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_optional_user] = lambda: user
    with TestClient(app) as test_client:
        yield test_client, user
    for dep in (get_db, get_current_user, get_optional_user):
        app.dependency_overrides.pop(dep, None)
