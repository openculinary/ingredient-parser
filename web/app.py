from flask import Flask, jsonify, request
from pint import UnitRegistry
import requests

from ingreedypy import Ingreedy


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


def parse_description(description):
    ingredient = {}
    for text in generate_subtexts(description):
        try:
            ingredient = Ingreedy().parse(text)
            break
        except Exception:
            continue

    result = {
        'description': description,
        'product': {
            'product': ingredient.get('ingredient'),
            'contents': [],
            'product_parser': 'ingreedypy',
        },
        'quantity': ingredient.get('amount'),
        'quantity_parser': 'ingreedypy',
        'units': ingredient.get('unit'),
        'units_parser': 'ingreedypy',
    }
    units = parse_units(result)
    if units:
        result.update(units)
    return result


def parse_descriptions(descriptions):
    ingredients_by_product = {}
    for description in descriptions:
        ingredient = parse_description(description)
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
            ingredient = ingredients_by_product[product]
            ingredient['product']['product'] = results.get(product)
            ingredient['product']['product_parser'] += '+graph'

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


def parse_units(ingredient):
    # Workaround: pint treats 'pinch' as 'pico-inch'
    # https://github.com/hgrecco/pint/issues/273
    if ingredient and ingredient.get('units') == 'pinch':
        ingredient['units'] = 'ml'
        ingredient['quantity'] = (ingredient.get('quantity') or 1) * 0.25

    try:
        quantity = unit_registry.Quantity(
            ingredient.get('quantity'),
            ingredient.get('units')
        )
    except Exception:
        return

    base_units = get_base_units(quantity)
    if base_units:
        quantity = quantity.to(base_units)

    result = {}
    result['quantity'] = round(quantity.magnitude, 2)
    if result.get('quantity_parser'):
        result['quantity_parser'] += '+pint'
    if base_units:
        result['units'] = base_units
        if result.get('units_parser'):
            result['units_parser'] += '+pint'
    return result


@app.route('/', methods=['POST'])
def root():
    descriptions = request.form.getlist('descriptions[]')
    descriptions = [d.strip().lower() for d in descriptions]

    ingredients = parse_descriptions(descriptions)

    return jsonify(ingredients)
