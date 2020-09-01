import pytest
import responses

from copy import deepcopy
import json

from web.app import (
    parse_description,
    parse_quantities,
    retrieve_knowledge,
)


def ingredient_parser_tests():
    return {
        'tomato': {
            'product': 'tomato',
            'magnitude': None,
            'units': None
        },
        '1 kilogram beef': {
            'product': 'beef',
            'magnitude': 1000,
            'units': 'g'
        },
        '1kg/2lb 4oz potatoes, cut into 5cm/2in chunks': {
            'product': 'potatoes, cut into 5cm/2in chunks',
            'magnitude': 1000,
            'units': 'g'
        },
        '1-½ ounce, weight vanilla ice cream': {
            'product': 'weight vanilla ice cream',
            'magnitude': 42.52,
            'units': 'g'
        },
    }.items()


@pytest.mark.parametrize('description, expected', ingredient_parser_tests())
def test_parse_description(description, expected):
    expected.update({'description': description})
    expected.update({'product': {
        'product': expected['product'],
        'product_id': None}
    })

    result = parse_description(description)
    del result['product']['product_parser']

    for field in expected:
        assert result[field] == expected[field]


@responses.activate
def test_knowledge_graph_query():
    knowledge = {
        'whole onion, diced': {
            'product': {
                'product': 'onion',
                'nutrition': {
                    'protein': 15.0,
                    'fat': 0.1,
                    'carbohydrates': 8.0,
                    'energy': 35.0,
                    'fibre': 2.0,
                }
            },
            'query': {'markup': 'whole <mark>onion</mark> diced'},
            'units': 'g',
            'magnitude': 110.0,
        },
        'splash of tomato ketchup': {
            'product': {
                'product': 'tomato ketchup',
                'nutrition': {
                    'protein': 1.5,
                    'fat': 0.1,
                    'carbohydrates': 28.5,
                    'energy': 115.0,
                    'fibre': 1.0,
                }
            },
            'query': {'markup': 'splash of <mark>tomato ketchup</mark>'},
            'units': 'ml',
            'magnitude': 3.0,
        },
        'plantains, peeled and chopped': {
            'product': {
                'product': 'plantains, peeled and chopped',
                'nutrition': None
            },
            'query': {'markup': '<mark>plantains, peeled and chopped</mark>'},
            'units': None,
            'magnitude': None,
        },
        'unknown': {
            'product': {'product': 'unknown'},
            'query': {'markup': '<mark>unknown</mark>'},
            'units': None,
            'magnitude': None,
        },
    }

    responses.add(
        responses.POST,
        'http://knowledge-graph-service/ingredients/query',
        body=json.dumps({'results': knowledge}),
    )

    results = retrieve_knowledge(deepcopy(knowledge))

    for description, ingredient in results.items():
        product = ingredient['product']
        nutrition = ingredient['nutrition']
        response = knowledge[description]

        assert product['product'] == response['product']['product']
        assert 'graph' in product['product_parser']
        assert nutrition == response['product'].get('nutrition', nutrition)


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
