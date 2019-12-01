import pytest

from web.app import parse_units


def parser_tests():
    return {
        '0.25 ml': {
            'parser': 'example',
            'product': 'paprika',
            'quantity': 1,
            'units': 'pinch'
        },
    }


@pytest.mark.parametrize('expected, ingredient', parser_tests().items())
def test_parse_units(expected, ingredient):
    result = parse_units(ingredient)
    result = '{} {}'.format(result['quantity'], result['units'])

    assert result == expected
