import pytest

from web.app import app


@pytest.fixture
def client():
    return app.test_client()


@pytest.fixture
@pytest.mark.respx(base_url="http://knowledge-graph-service")
def knowledge_graph_stub(respx_mock):
    respx_mock.post("/ingredients/query").respond(status_code=500)
