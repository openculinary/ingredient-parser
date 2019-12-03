from mock import patch


def nyt_parser_stub(descriptions):
    return [{'input': description} for description in descriptions]


@patch('web.app.parse_descriptions_nyt', nyt_parser_stub)
def test_request(client):
    response = client.post('/', data={
        'descriptions[]': [
            '100ml red wine',
            '1000 grams potatoes',
            '2lb 4oz potatoes',
            'pinch salt',
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
    }, {
        'description': '2lb 4oz potatoes',
        'product': {
            'product': 'potatoes',
            'product_parser': 'ingreedypy',
        },
        'units': 'g',
        'units_parser': 'ingreedypy+pint',
        'quantity': 907.18,
        'quantity_parser': 'ingreedypy+pint'
    }, {
        'description': 'pinch salt',
        'product': {
            'product': 'salt',
            'product_parser': 'ingreedypy',
        },
        'units': 'ml',
        'units_parser': 'ingreedypy+pint',
        'quantity': 0.25,
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
        'quantity': 453.59,
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
