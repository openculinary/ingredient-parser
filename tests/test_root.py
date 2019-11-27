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
def test_request(description, expected):
    expected.update({'input': description, 'parser': 'ingreedypy'})

    result = parse_description_ingreedypy(description)

    assert result == expected
