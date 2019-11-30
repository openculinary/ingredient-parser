from mock import patch
import pytest

from web.app import merge_ingredients, parse_description_ingreedypy


@pytest.fixture
def sample_ingredient():
    return {
        'description': '1 block firm tofu',
        'product': 'tofu',
        'units': 'block',
        'quantity': 1
    }


def parser_tests():
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
    }


@pytest.mark.parametrize('description, expected', parser_tests().items())
def test_parse_description_ingreedypy(description, expected):
    expected.update({'description': description, 'parser': 'ingreedypy'})

    result = parse_description_ingreedypy(description)

    assert result == expected


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


def nyt_parser_stub(descriptions):
    return [{'input': description} for description in descriptions]


@patch('web.app.parse_descriptions_nyt', nyt_parser_stub)
def test_request(client):
    response = client.post('/', data={
        'descriptions[]': [
            '100ml red wine',
            '1000 grams potatoes',
        ]
    })

    assert response.json == [{
        'description': '100ml red wine',
        'product': {
            'product': 'red wine',
            'product_parser': 'ingreedypy',
        },
        'units': 'ml',
        'units_parser': 'ingreedypy+pint',
        'quantity': 100,
        'quantity_parser': 'ingreedypy+pint'
    }, {
        'description': '1000 grams potatoes',
        'product': {
            'product': 'potatoes',
            'product_parser': 'ingreedypy',
        },
        'units': 'g',
        'units_parser': 'ingreedypy+pint',
        'quantity': 1000,
        'quantity_parser': 'ingreedypy+pint'
    }]


@patch('web.app.parse_descriptions_nyt', nyt_parser_stub)
def test_request_dimensionless(client):
    response = client.post('/', data={'descriptions[]': ['1 potato']})

    assert response.json == [{
        'description': '1 potato',
        'product': {
            'product': 'potato',
            'product_parser': 'ingreedypy',
        },
        'quantity': 1,
        'quantity_parser': 'ingreedypy+pint'
    }]


@patch('web.app.parse_units')
@patch('web.app.parse_descriptions_nyt', nyt_parser_stub)
def test_request_unit_parse_failure(parse_units, client):
    parse_units.return_value = None

    response = client.post('/', data={'descriptions[]': ['100ml red wine']})

    assert response.json == [{
        'description': '100ml red wine',
        'product': {
            'product': 'red wine',
            'product_parser': 'ingreedypy',
        },
        'units': 'milliliter',
        'units_parser': 'ingreedypy',
        'quantity': 100,
        'quantity_parser': 'ingreedypy'
    }]


@patch('web.app.parse_descriptions_nyt', nyt_parser_stub)
def test_parser_fallbacks(client):
    response = client.post('/', data={'descriptions[]': [
        '500g/1lb potatoes',
        '1lb/500g potatoes',
        '/500g potatoes',
    ]})

    assert response.json == [{
        'description': '500g/1lb potatoes',
        'product': {
            'product': 'potatoes',
            'product_parser': 'ingreedypy',
        },
        'quantity': 500,
        'quantity_parser': 'ingreedypy+pint',
        'units': 'g',
        'units_parser': 'ingreedypy+pint'
    }, {
        'description': '1lb/500g potatoes',
        'product': {
            'product': 'potatoes',
            'product_parser': 'ingreedypy',
        },
        'quantity': 453,
        'quantity_parser': 'ingreedypy+pint',
        'units': 'g',
        'units_parser': 'ingreedypy+pint'
    }, {
        'description': '/500g potatoes',
        'product': {
            'product': 'potatoes',
            'product_parser': 'ingreedypy',
        },
        'quantity': 500,
        'quantity_parser': 'ingreedypy+pint',
        'units': 'g',
        'units_parser': 'ingreedypy+pint'
    }]
