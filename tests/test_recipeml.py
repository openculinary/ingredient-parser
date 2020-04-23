import pytest
from web.recipeml import merge


def recipeml_tests():
    return {
        'red wine': {
            'markup': '<mark>red wine</mark>',
            'quantity': 100,
            'units': 'ml',
        },
        'potatoes au gratin': {
            'markup': '<mark>potatoes</mark> au gratin',
            'units': 'g',
            'quantity': 500,
        },
        'firm tofu': {
            'markup': '<mark>firm tofu</mark>',
            'quantity': 1,
            'units': 'block',
        },
        'pinch salt': {
            'markup': 'pinch of <mark>salt</mark>',
            'units': 'ml',
            'quantity': 0.25,
        },
    }.items()


def expected_markup(ingredient):
    markup, quantity, units = (
        ingredient['markup'],
        ingredient['quantity'],
        ingredient['units'],
    )
    amount_markup = f'<amt><qty>{quantity}</qty><unit>{units}</unit></amt>'
    ingredient_markup = markup.replace('mark>', 'ingredient>')
    return amount_markup + ingredient_markup


@pytest.mark.parametrize('_, ingredient', recipeml_tests())
def test_request(_, ingredient):
    expected = expected_markup(ingredient)
    result = merge(
        ingredient_markup=ingredient['markup'],
        quantity=ingredient['quantity'],
        units=ingredient['units']
    )
    assert result == expected
