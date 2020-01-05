import pytest
import responses

import json

from web.app import (
    parse_description,
    parse_descriptions,
    parse_quantities,
)


def ingredient_parser_tests():
    return {
        'tomato': {
            'product': 'tomato',
            'quantity': None,
            'units': None
        },
        '1 kilogram beef': {
            'product': 'beef',
            'quantity': 1000,
            'units': 'g'
        },
        '1kg/2lb 4oz potatoes, cut into 5cm/2in chunks': {
            'product': 'potatoes, cut into 5cm/2in chunks',
            'quantity': 1000,
            'units': 'g'
        },
        '1-½ ounce, weight vanilla ice cream': {
            'product': 'weight vanilla ice cream',
            'quantity': 42.52,
            'units': 'g'
        },
    }.items()


@pytest.mark.parametrize('description, expected', ingredient_parser_tests())
def test_parse_description(description, expected):
    expected.update({'description': description})
    expected.update({'product': {'product': expected['product']}})

    result = parse_description(description)
    del result['product']['product_parser']

    for field in expected:
        assert result[field] == expected[field]


@responses.activate
def test_knowledge_graph_query():
    descriptions_to_products = {
        'whole onion, diced': 'onion',
        'splash of tomato ketchup': 'tomato ketchup',
        'plantains, peeled and chopped': None,
    }

    response = {
        'results': {
            d: {'product': p} if p else None
            for d, p in descriptions_to_products.items()
        }
    }
    responses.add(
        responses.POST,
        'http://knowledge-graph-service/ingredients/query',
        body=json.dumps(response),
    )

    results = parse_descriptions(list(descriptions_to_products.keys()))
    for result in results:
        description = result['description']
        fixture_product = descriptions_to_products.get(description)

        if fixture_product is None:
            assert result['product']['product'] == description
            assert 'graph' not in result['product']['product_parser']
        else:
            assert result['product']['product'] == fixture_product
            assert 'graph' in result['product']['product_parser']


def unit_parser_tests():
    return {
        '0.25 ml': {
            'quantity': [{'amount': 1, 'unit': 'pinch'}],
            'product': {'product': 'paprika'},
        },
    }.items()


@pytest.mark.parametrize('expected, ingredient', unit_parser_tests())
def test_parse_quantity(expected, ingredient):
    quantity, units, parser = parse_quantities(ingredient)
    result = '{} {}'.format(quantity, units)

    assert result == expected
