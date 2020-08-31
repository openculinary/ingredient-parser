from flask import Flask, jsonify, request
from pint import UnitRegistry
import requests

from ingreedypy import Ingreedy

from web.recipeml import render


app = Flask(__name__)
unit_registry = UnitRegistry()


def generate_subtexts(description):
    yield description
    if '/' in description:
        pre_text, post_text = description.split('/', 1)
        post_tokens = post_text.split(' ')
        if pre_text:
            yield u'{} {}'.format(pre_text, u' '.join(post_tokens[1:]))
        yield u' '.join(post_tokens)
    yield description.replace(',', '')


def parse_quantity(quantity):
    # Workaround: pint treats 'pinch' as 'pico-inch'
    # https://github.com/hgrecco/pint/issues/273
    if quantity['unit'] == 'pinch':
        quantity['unit'] = 'ml'
        quantity['amount'] = (quantity.get('amount') or 1) * 0.25

    quantity = unit_registry.Quantity(quantity['amount'], quantity['unit'])
    return quantity.to(get_base_units(quantity) or quantity.units)


def parse_quantities(ingredient):
    parser = 'ingreedypy'
    quantities = ingredient.get('quantity') or []
    if not quantities:
        return None, None, parser

    result = 0
    for quantity in quantities:
        try:
            result += parse_quantity(quantity)
            parser = 'ingreedypy+pint'
        except Exception:
            return None, None, parser

    if not result > 0:
        return None, None, parser

    units = None
    if not result.dimensionless:
        units = unit_registry.get_symbol(str(result.units))
    return round(result.magnitude, 2), units, parser


def parse_description(description):
    product = description
    product_parser = None
    magnitude = None
    units = None
    parser = None

    for text in generate_subtexts(description):
        try:
            ingredient = Ingreedy().parse(text)
            product = ingredient['ingredient']
            product_parser = 'ingreedypy'
            magnitude, units, parser = parse_quantities(ingredient)
            break
        except Exception:
            raise
            continue

    return {
        'description': description,
        'product': {
            'product_id': None,
            'product': product,
            'product_parser': product_parser,
        },
        'markup': f'<mark>{product}</mark>',
        'magnitude': magnitude,
        'magnitude_parser': parser,
        'units': units,
        'units_parser': parser,
    }


def parse_descriptions(descriptions):
    ingredients_by_product = {}
    for description in descriptions:
        try:
            ingredient = parse_description(description)
        except Exception as e:
            raise Exception(f'Parsing failed: "{description}" - {e}')
        product = ingredient['product']['product']
        ingredients_by_product[product] = ingredient

    ingredient_data = requests.post(
        url='http://knowledge-graph-service/ingredients/query',
        data={'descriptions[]': list(ingredients_by_product.keys())},
        proxies={}
    )
    if ingredient_data.ok:
        results = ingredient_data.json()['results']
        for product in results:
            if results[product]['product'] is None:
                continue
            ingredient = ingredients_by_product[product]
            ingredient['markup'] = results[product]['query']['markup']
            ingredient['product'] = results[product]['product']
            ingredient['product']['product_parser'] = 'knowledge-graph'

            # TODO: Remove this remapping once the database handles native IDs
            if 'id' in ingredient['product']:
                ingredient['product']['product_id'] = \
                    ingredient['product'].pop('id')

    for product, ingredient in ingredients_by_product.items():
        ingredients_by_product[product]['markup'] = render(ingredient)
    return list(ingredients_by_product.values())


def get_base_units(quantity):
    dimensionalities = {
        None: unit_registry.Quantity(1),
        'length': unit_registry.Quantity(1, 'cm'),
        'volume': unit_registry.Quantity(1, 'ml'),
        'weight': unit_registry.Quantity(1, 'g'),
    }
    dimensionalities = {
        v.dimensionality: unit_registry.get_symbol(str(v.units)) if k else None
        for k, v in dimensionalities.items()
    }
    return dimensionalities.get(quantity.dimensionality)


@app.route('/', methods=['POST'])
def root():
    descriptions = request.form.getlist('descriptions[]')
    descriptions = [d.strip() for d in descriptions]

    ingredients = parse_descriptions(descriptions)

    return jsonify(ingredients)
