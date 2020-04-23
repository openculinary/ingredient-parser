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
    description_responses = {
        'whole onion, diced': {
            'product': {'product': 'onion'},
            'query': {'markup': 'whole <mark>onion</mark> diced'},
        },
        'splash of tomato ketchup': {
            'product': {'product': 'tomato ketchup'},
            'query': {'markup': 'splash of <mark>tomato ketchup</mark>'},
        },
        'plantains, peeled and chopped': {
            'product': {'product': 'plantains, peeled and chopped'},
            'query': {'markup': '<mark>plantains, peeled and chopped</mark>'},
        },
    }

    response = {
        'results': {
            d: r if r else None
            for d, r in description_responses.items()
        }
    }
    responses.add(
        responses.POST,
        'http://knowledge-graph-service/ingredients/query',
        body=json.dumps(response),
    )

    results = parse_descriptions(list(description_responses.keys()))
    for result in results:
        description = result['description']
        markup = result['markup'].replace('ingredient>', 'mark>')
        product = result['product']
        response = description_responses.get(description)

        if not response:
            assert markup == description
            assert product['product'] == description
            assert 'graph' not in result['product']['product_parser']
        else:
            assert markup == response['query']['markup']
            assert product['product'] == response['product']['product']
            assert 'graph' in product['product_parser']


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
