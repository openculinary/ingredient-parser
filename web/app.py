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


def parse_quantity(quantity):
    # Workaround: pint treats 'pinch' as 'pico-inch'
    # https://github.com/hgrecco/pint/issues/273
    if quantity['unit'] == 'pinch':
        quantity['unit'] = 'ml'
        quantity['amount'] = (quantity.get('amount') or 1) * 0.25

    try:
        quantity = unit_registry.Quantity(
            quantity['amount'],
            quantity['unit']
        )
    except Exception:
        return

    base_units = get_base_units(quantity)
    if base_units:
        quantity = quantity.to(base_units)
    return quantity


def parse_quantities(ingredient):
    magnitude, units, parser = 0, None, 'ingreedypy'

    total = 0
    for quantity in ingredient.get('quantity') or []:
        total += parse_quantity(quantity) or 0

    if total:
        magnitude = round(total.magnitude, 2)
        parser = f'{parser}+pint'
        if not total.dimensionless:
            units = unit_registry.get_symbol(str(total.units))

    return magnitude or None, units, parser


def parse_description(description):
    ingredient = {}
    for text in generate_subtexts(description):
        try:
            ingredient = Ingreedy().parse(text)
            break
        except Exception:
            continue

    parsed_product = ingredient.get('ingredient')
    product = {
        'product': parsed_product or description,
        'product_parser': 'ingreedypy' if parsed_product else None,
    }

    quantity, units, parser = parse_quantities(ingredient)
    return {
        'description': description,
        'product': product,
        'markup': parsed_product or description,
        'quantity': quantity,
        'quantity_parser': parser,
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
            if results[product] is None:
                continue
            ingredient = ingredients_by_product[product]
            ingredient['product'] = results[product]
            ingredient['product']['product_parser'] = 'knowledge-graph'
            ingredient['markup'] = results[product]['query']['markup']

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
    descriptions = [d.strip().lower() for d in descriptions]

    ingredients = parse_descriptions(descriptions)

    return jsonify(ingredients)
