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
            'quantity': 5,
        },
        'firm tofu': {
            'markup': '<mark>firm tofu</mark>',
            'quantity': 1,
            'units': 'block',
        },
        'pinch salt': {
            'markup': 'pinch of <mark>salt</mark>',
            'units': 'pinch',
        },
    }.items()


def expected_markup(ingredient):
    markup, quantity, units = (
        ingredient['markup'],
        ingredient.get('quantity'),
        ingredient.get('units'),
    )
    amount_markup = '<amt>'
    amount_markup += f'<qty>{quantity}</qty>' if quantity else ''
    amount_markup += f'<unit>{units}</unit>' if units else ''
    amount_markup += '</amt>'
    ingredient_markup = markup.replace('mark>', 'ingredient>')
    return amount_markup + ingredient_markup


@pytest.mark.parametrize('_, ingredient', recipeml_tests())
def test_request(_, ingredient):
    expected = expected_markup(ingredient)
    result = merge(
        ingredient_markup=ingredient['markup'],
        quantity=ingredient.get('quantity'),
        units=ingredient.get('units')
    )
    assert result == expected


def test_entity_escaping():
    markup = '&amp; <mark>example</mark>'
    quantity = 1

    expected = '<amt><qty>1</qty></amt>&amp; <ingredient>example</ingredient>'
    result = merge(markup, quantity, None)

    assert result == expected
