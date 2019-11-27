from mock import patch
import pytest

from web.app import parse_description_ingreedypy


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
    expected.update({'input': description, 'parser': 'ingreedypy'})

    result = parse_description_ingreedypy(description)

    assert result == expected


def nyt_parser_stub(descriptions):
    return [{'input': description} for description in descriptions]


@patch('web.app.parse_descriptions_nyt', nyt_parser_stub)
def test_request(client):
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
