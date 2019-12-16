import pytest
import responses

import json

from web.app import (
    parse_description,
    parse_descriptions,
    parse_units,
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
    del result['product']['contents']

    for field in expected:
        assert result[field] == expected[field]


@responses.activate
def test_knowledge_graph_query():
    descriptions_to_products = {
        'whole onion, diced': 'onion',
        'splash of tomato ketchup': 'tomato ketchup',
    }

    response = {'results': {d: p for d, p in descriptions_to_products.items()}}
    responses.add(
        responses.POST,
        'http://knowledge-graph-service/ingredients/query',
        body=json.dumps(response),
    )

    results = parse_descriptions(list(descriptions_to_products.keys()))
    for result in results:
        description = result['description']
        expected_product = descriptions_to_products.get(description)

        assert result['product']['product'] == expected_product
        assert 'graph' in result['product']['product_parser']


def unit_parser_tests():
    return {
        '0.25 ml': {
            'product': {'product': 'paprika'},
            'quantity': 1,
            'units': 'pinch',
        },
    }.items()


@pytest.mark.parametrize('expected, ingredient', unit_parser_tests())
def test_parse_units(expected, ingredient):
    result = parse_units(ingredient)
    result = '{} {}'.format(result['quantity'], result['units'])

    assert result == expected
