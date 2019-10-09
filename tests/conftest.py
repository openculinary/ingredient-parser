import pytest

from web.app import app


@pytest.fixture
def client():
    return app.test_client()
