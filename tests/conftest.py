"""Test setup. Env vars are set *before* the app is imported so the app
uses a throwaway database and upload folder instead of the real ones."""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="geomeasure_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["UPLOAD_DIRECTORY"] = f"{_TMP}/uploads"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from tests import data_factory  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def kml_file(tmp_path):
    return data_factory.write_kml(tmp_path / "survey.kml")


@pytest.fixture
def shapefile_zip(tmp_path):
    return data_factory.write_shapefile_zip(tmp_path / "survey.zip")
