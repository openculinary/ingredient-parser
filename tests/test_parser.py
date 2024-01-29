import pytest

from copy import deepcopy

from web.app import (
    attach_nutrition,
    parse_description,
    parse_quantities,
    retrieve_knowledge,
)


def ingredient_parser_tests():
    return {
        "tomato": {"product": "tomato", "magnitude": None, "units": None},
        "1 kilogram beef": {"product": "beef", "magnitude": 1000, "units": "g"},
        "1kg/2lb 4oz potatoes, cut into 5cm/2in chunks": {
            "product": "potatoes, cut into 5cm/2in chunks",
            "magnitude": 1000,
            "units": "g",
        },
        "1-½ ounce, weight vanilla ice cream": {
            "product": "weight vanilla ice cream",
            "magnitude": 42.52,
            "units": "g",
        },
    }.items()


@pytest.mark.parametrize("description, expected", ingredient_parser_tests())
def test_parse_description(description, expected):
    expected.update({"description": description})
    expected.update({"product": {"product": expected["product"], "id": None}})

    result = parse_description(description)
    del result["product"]["product_parser"]

    for field in expected:
        assert result[field] == expected[field]


@pytest.mark.respx(base_url="http://knowledge-graph-service")
def test_knowledge_graph_query(respx_mock):
    knowledge = {
        "whole onion, diced": {
            "product": {
                "product": "onion",
                "nutrition": {
                    "protein": 15.0,
                    "fat": 0.1,
                    "carbohydrates": 8.0,
                    "energy": 35.0,
                    "fibre": 2.0,
                },
            },
            "query": {"markup": "whole <mark>onion</mark> diced"},
            "units": "g",
            "magnitude": 110.0,
        },
        "splash of tomato ketchup": {
            "product": {
                "product": "tomato ketchup",
                "nutrition": {
                    "protein": 1.5,
                    "fat": 0.1,
                    "carbohydrates": 28.5,
                    "energy": 115.0,
                    "fibre": 1.0,
                },
            },
            "query": {"markup": "splash of <mark>tomato ketchup</mark>"},
            "units": "ml",
            "magnitude": 3.0,
        },
        "chunk of butter": {
            "product": {
                "product": "butter",
                "nutrition": {
                    "protein": 0.5,
                    "fat": 82.0,
                    "carbohydrates": 0.5,
                    "energy": 745.0,
                    "fibre": None,
                },
            },
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

    expected_nutrition = {
        "whole onion, diced": {
            "protein": 16.5,
            "fat": 0.11,
            "carbohydrates": 8.8,
            "energy": 38.5,
            "fibre": 2.2,
        },
        "splash of tomato ketchup": {
            "protein": 0.04,
            "fat": 0.0,
            "carbohydrates": 0.85,
            "energy": 3.45,
            "fibre": 0.03,
        },
        "chunk of butter": {
            "protein": round(0.5 * 0.911 / 4, 2),
            "fat": round(82.0 * 0.911 / 4, 2),
            "carbohydrates": round(0.5 * 0.911 / 4, 2),
            "energy": round(745.0 * 0.911 / 4, 2),
            "fibre": round(0.0 * 0.911 / 4, 2),
        },
    }

    respx_mock.post("/ingredients/query").respond(json={"results": knowledge})

    results = retrieve_knowledge(deepcopy(knowledge))
    results = attach_nutrition(results)

    for description, ingredient in results.items():
        product = ingredient["product"]
        product_expected = knowledge[description]["product"]["product"]

        nutrition = ingredient["nutrition"]
        nutrition = (
            None
            if nutrition is None
            else {
                nutrient: amount
                for nutrient, amount in nutrition.items()
                if not nutrient.endswith("_units")
            }
        )
        nutrition_expected = expected_nutrition.get(description)

        if ingredient.get("units") == "ml":
            assert ingredient["relative_density"] is not None

        assert product["product"] == product_expected
        assert "graph" in product["product_parser"]
        assert nutrition == nutrition_expected


def unit_parser_tests():
    return {
        "0.35 g": {
            "quantity": [{"amount": 1, "unit": "pinch"}],
            "product": {"product": "paprika"},
        },
    }.items()


@pytest.mark.parametrize("expected, ingredient", unit_parser_tests())
def test_parse_quantity(expected, ingredient):
    quantity, units, parser = parse_quantities(ingredient)
    result = f"{quantity} {units}"

    assert result == expected
