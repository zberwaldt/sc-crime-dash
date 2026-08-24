import os
import sys

SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
sys.path.insert(0, SRC_DIR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest

from tests.fake_db import MockDatabase


@pytest.fixture
def mock_db():
    """A real in-memory SQLite database with the app's tables pre-seeded.

    Pass it (it duck-types as an engine via .connect()) to any fetch
    function's ``engine=`` argument to run the actual SQL in src/queries.py
    without a running PostGIS server.
    """
    db = MockDatabase()
    yield db
    db.dispose()
