from mock import patch
import pytest


def request_tests():
    return {
        '100ml red wine': {
            'product': 'red wine',
            'quantity': 100,
            'units': 'ml',
        },
        '1000 grams potatoes': {
            'product': 'potatoes',
            'units': 'g',
            'quantity': 1000,
        },
        '2lb 4oz potatoes': {
            'product': 'potatoes',
            'quantity': 907.18,
            'units': 'g',
        },
        'pinch salt': {
            'product': 'salt',
            'units': 'ml',
            'quantity': 0.25,
        },
    }.items()


@pytest.mark.parametrize('description,expected', request_tests())
def test_request(client, description, expected):
    response = client.post('/', data={'descriptions[]': description})
    ingredient = response.json[0]

    assert ingredient['product']['product'] == expected['product']
    assert ingredient['quantity'] == expected['quantity']
    assert ingredient['units'] == expected['units']


def test_request_dimensionless(client):
    response = client.post('/', data={'descriptions[]': ['1 potato']})
    ingredient = response.json[0]

    assert ingredient['product']['product'] == 'potato'
    assert ingredient['quantity'] == 1


@patch('web.app.parse_units')
def test_request_unit_parse_failure(parse_units, client):
    parse_units.return_value = None

    response = client.post('/', data={'descriptions[]': ['100ml red wine']})
    ingredient = response.json[0]

    assert 'pint' not in ingredient['quantity_parser']
    assert 'pint' not in ingredient['units_parser']
