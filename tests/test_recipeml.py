import pytest
from web.recipeml import render


def recipeml_tests():
    return {
        'red wine': {
            'markup': '<mark>red wine</mark>',
            'magnitude': 100,
            'units': 'ml',
        },
        'potatoes au gratin': {
            'markup': '<mark>potatoes</mark> au gratin',
            'magnitude': 5,
        },
        'firm tofu': {
            'markup': '<mark>firm tofu</mark>',
            'magnitude': 1,
            'units': 'block',
        },
        'pinch salt': {
            'markup': 'pinch of <mark>salt</mark>',
            'units': 'pinch',
        },
    }.items()


def expected_markup(ingredient):
    markup, magnitude, units = (
        ingredient['markup'],
        ingredient.get('magnitude'),
        ingredient.get('units'),
    )
    amount_markup = '<amt>'
    amount_markup += f'<qty>{magnitude}</qty>' if magnitude else ''
    amount_markup += f'<unit>{units}</unit>' if units else ''
    amount_markup += '</amt>'
    ingredient_markup = markup.replace('mark>', 'ingredient>')
    return amount_markup + ingredient_markup


@pytest.mark.parametrize('_, ingredient', recipeml_tests())
def test_request(_, ingredient):
    expected = expected_markup(ingredient)
    result = render(ingredient)
    assert result == expected


def test_entity_escaping():
    ingredient = {
        'markup': '&amp; <mark>example</mark>',
        'magnitude': 1,
    }

    expected = '<amt><qty>1</qty></amt>&amp; <ingredient>example</ingredient>'
    result = render(ingredient)

    assert result == expected
