import pytest
import responses

from web.app import app


@pytest.fixture
def client():
    return app.test_client()


@pytest.fixture
def knowledge_graph_stub():
    with responses.RequestsMock() as response:
        response.add(
            responses.POST,
            "http://knowledge-graph-service/ingredients/query",
            status=500,
        )
        yield response
