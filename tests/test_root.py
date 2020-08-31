import pytest
from unittest.mock import patch


def request_tests():
    return {
        '100ml red wine': {
            'product': 'red wine',
            'magnitude': 100,
            'units': 'ml',
        },
        '1000 grams potatoes': {
            'product': 'potatoes',
            'magnitude': 1000,
            'units': 'g',
        },
        '2lb 4oz potatoes': {
            'product': 'potatoes',
            'magnitude': 1020.58,
            'units': 'g',
        },
        'pinch salt': {
            'product': 'salt',
            'magnitude': 0.25,
            'units': 'ml',
        },
    }.items()


@pytest.mark.parametrize('description,expected', request_tests())
def test_request(client, knowledge_graph_stub, description, expected):
    response = client.post('/', data={'descriptions[]': description})
    ingredient = response.json[0]

    assert ingredient['product']['product'] == expected['product']
    assert ingredient['magnitude'] == expected['magnitude']
    assert ingredient['units'] == expected['units']


def test_request_dimensionless(client, knowledge_graph_stub):
    response = client.post('/', data={'descriptions[]': ['1 potato']})
    ingredient = response.json[0]

    assert ingredient['product']['product'] == 'potato'
    assert ingredient['magnitude'] == 1


@patch('web.app.parse_quantity')
def test_parse_quantity_failure(parse_quantity, client, knowledge_graph_stub):
    parse_quantity.side_effect = Exception

    response = client.post('/', data={'descriptions[]': ['100ml red wine']})
    ingredient = response.json[0]

    assert 'pint' not in ingredient['magnitude_parser']
    assert 'pint' not in ingredient['units_parser']
