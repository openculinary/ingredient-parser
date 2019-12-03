# -*- coding: utf-8 -*-

import pytest

from web.app import (
    merge_ingredients,
    parse_description_ingreedypy,
    parse_units,
)


@pytest.fixture
def sample_ingredient():
    return {
        'description': '1 block firm tofu',
        'product': 'tofu',
        'units': 'block',
        'quantity': 1
    }


def ingredient_parser_tests():
    return {
        'tomato': {
            'product': 'tomato',
            'quantity': None,
            'units': None
        },
        '1 kilogram beef': {
            'product': 'beef',
            'quantity': 1,
            'units': 'kilogram'
        },
        '1kg/2lb 4oz potatoes, cut into 5cm/2in chunks': {
            'product': 'potatoes, cut into 5cm/2in chunks',
            'quantity': 1,
            'units': 'kilogram'
        },
        '1-½ ounce, weight vanilla ice cream': {
            'product': 'weight vanilla ice cream',
            'quantity': 1.5,
            'units': 'ounce'
        },
    }.items()


@pytest.mark.parametrize('description, expected', ingredient_parser_tests())
def test_parse_description_ingreedypy(description, expected):
    expected.update({'description': description, 'parser': 'ingreedypy'})

    result = parse_description_ingreedypy(description)

    assert result == expected


def test_merge_ingredient_quantity_heuristic(sample_ingredient):
    ingredient_a = sample_ingredient.copy()
    ingredient_a.update({
        'description': '12 units of ingredient',
        'parser': 'a',
        'quantity': 1,
        'units': 'a'
    })

    ingredient_b = sample_ingredient.copy()
    ingredient_b.update({
        'description': '12 units of ingredient',
        'parser': 'b',
        'quantity': 12,
        'units': 'b'
    })

    merged_ingredient = merge_ingredients(ingredient_a, ingredient_b)

    assert merged_ingredient['quantity'] == 12
    assert merged_ingredient['units'] == 'b'


def test_merge_ingredient_unit_fallback(sample_ingredient):
    ingredient_a = sample_ingredient.copy()
    ingredient_a.update({
        'parser': 'a',
        'units': 'unparseable',
        'quantity': 1
    })

    ingredient_b = sample_ingredient.copy()
    ingredient_b.update({
        'parser': 'b',
        'units': 'g',
        'quantity': 500
    })

    merged_ingredient = merge_ingredients(ingredient_a, ingredient_b)

    assert merged_ingredient == {
        'description': '1 block firm tofu',
        'product': {
            'product': 'tofu',
            'product_parser': 'a'
        },
        'units': 'g',
        'units_parser': 'b+pint',
        'quantity': 500,
        'quantity_parser': 'b+pint'
    }


def test_merge_ingredient_unit_fallback_missing(sample_ingredient):
    ingredient_a = sample_ingredient.copy()
    ingredient_a.update({'parser': 'a'})

    for args in [(ingredient_a, None), (None, ingredient_a)]:
        merged_ingredient = merge_ingredients(*args)

        assert merged_ingredient is not None
        assert merged_ingredient['units_parser'] == 'a'


def unit_parser_tests():
    return {
        '0.25 ml': {
            'parser': 'example',
            'product': 'paprika',
            'quantity': 1,
            'units': 'pinch'
        },
    }.items()


@pytest.mark.parametrize('expected, ingredient', unit_parser_tests())
def test_parse_units(expected, ingredient):
    result = parse_units(ingredient)
    result = '{} {}'.format(result['quantity'], result['units'])

    assert result == expected
