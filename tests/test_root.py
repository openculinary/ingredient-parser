import pytest
from unittest.mock import patch


def request_tests():
    return {
        ("en", "100ml red wine"): {
            "product": "red wine",
            "magnitude": 100,
            "units": "ml",
        },
        ("en", "1000 grams potatoes"): {
            "product": "potatoes",
            "magnitude": 1000,
            "units": "g",
        },
        ("en", "2lb 4oz potatoes"): {
            "product": "potatoes",
            "magnitude": 1020.58,
            "units": "g",
        },
        ("en", "pinch salt"): {
            "product": "salt",
            "magnitude": 0.35,
            "units": "g",
        },
        ("en", "2ml olive oil"): {
            "product": "olive oil",
            "magnitude": 2,
            "units": "ml",
        },
        ("en", "20ml sweet & sour"): {
            "product": "sweet & sour",
            "magnitude": 20,
            "units": "ml",
        },
    }.items()


@pytest.mark.parametrize("context, expected", request_tests())
@pytest.mark.respx(base_url="http://knowledge-graph-service", using="httpx")
def test_request(client, knowledge_graph_stub, context, expected):
    language_code, description = context
    response = client.post(
        "/",
        data={
            "language_code": language_code,
            "descriptions[]": description,
        },
    )
    ingredient = response.json[0]

    assert ingredient["product"]["product"] == expected["product"]
    assert ingredient["magnitude"] == expected["magnitude"]
    assert ingredient["units"] == expected["units"]


@pytest.mark.respx(base_url="http://knowledge-graph-service", using="httpx")
def test_request_dimensionless(client, knowledge_graph_stub):
    response = client.post(
        "/",
        data={
            "language_code": "en",
            "descriptions[]": ["1 potato"],
        },
    )
    ingredient = response.json[0]

    assert ingredient["product"]["product"] == "potato"
    assert ingredient["magnitude"] == 1


@patch("web.app.parse_quantity")
@pytest.mark.respx(base_url="http://knowledge-graph-service", using="httpx")
def test_parse_quantity_failure(parse_quantity, client, knowledge_graph_stub):
    parse_quantity.side_effect = Exception

    response = client.post(
        "/",
        data={
            "language_code": "en",
            "descriptions[]": ["100ml red wine"],
        },
    )
    ingredient = response.json[0]

    assert "pint" not in ingredient["magnitude_parser"]
    assert "pint" not in ingredient["units_parser"]
