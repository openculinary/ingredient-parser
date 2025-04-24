import pytest

from copy import deepcopy

from web.app import (
    parse_description,
    parse_quantities,
    retrieve_knowledge,
)


def ingredient_parser_tests():
    return {
        ("en", "tomato"): {"product": "tomato", "magnitude": None, "units": None},
        ("en", "1 kilogram beef"): {"product": "beef", "magnitude": 1000, "units": "g"},
        ("en", "1kg/2lb 4oz potatoes, cut into 5cm/2in chunks"): {
            "product": "potatoes, cut into 5cm/2in chunks",
            "magnitude": 1000,
            "units": "g",
        },
        ("en", "1-½ ounce, weight vanilla ice cream"): {
            "product": "weight vanilla ice cream",
            "magnitude": 42.52,
            "units": "g",
        },
    }.items()


@pytest.mark.parametrize("context, expected", ingredient_parser_tests())
def test_parse_description(context, expected):
    language_code, description = context
    expected.update({"description": description})
    expected.update({"product": {"product": expected["product"], "id": None}})

    result = parse_description(language_code, description)
    del result["product"]["product_parser"]

    for field in expected:
        assert result[field] == expected[field]


@pytest.mark.respx(base_url="http://knowledge-graph-service", using="httpx")
def test_knowledge_graph_query(respx_mock):
    knowledge = {
        "whole onion, diced": {
            "product": {"product": "onion"},
            "query": {"markup": "whole <mark>onion</mark> diced"},
            "units": "g",
            "magnitude": 110.0,
        },
        "splash of tomato ketchup": {
            "product": {"product": "tomato ketchup"},
            "query": {"markup": "splash of <mark>tomato ketchup</mark>"},
            "units": "ml",
            "magnitude": 3.0,
        },
        "chunk of butter": {
            "product": {"product": "butter"},
            "query": {"markup": "chunk of <mark>butter</mark>"},
            "units": "ml",
            "magnitude": 25.0,
        },
        "plantains, peeled and chopped": {
            "product": {"product": "plantains, peeled and chopped"},
            "query": {"markup": "<mark>plantains, peeled and chopped</mark>"},
        },
        "unknown": {
            "product": {"product": "unknown"},
            "query": {"markup": "<mark>unknown</mark>"},
        },
    }

    respx_mock.post("/ingredients/query").respond(json={"results": knowledge})

    results = retrieve_knowledge(deepcopy(knowledge))

    for description, ingredient in results.items():
        product = ingredient["product"]
        product_expected = knowledge[description]["product"]["product"]

        assert product["product"] == product_expected
        assert "graph" in product["product_parser"]


def unit_parser_tests():
    return {
        "0.35 g": (
            "en",
            {
                "quantity": [{"amount": 1, "unit": "pinch"}],
                "product": {"product": "paprika"},
            },
        ),
    }.items()


@pytest.mark.parametrize("expected, context", unit_parser_tests())
def test_parse_quantity(expected, context):
    language_code, ingredient = context
    quantity, units, parser = parse_quantities(language_code, ingredient)
    result = f"{quantity} {units}"

    assert result == expected
