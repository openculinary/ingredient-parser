import pytest

from web.app import (
    parse_description,
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
