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


def determine_nutritional_content(ingredient):
    nutrition = ingredient['product'].pop('nutrition', None)
    if not nutrition:
        return None
    if not ingredient.get('units'):
        return None
    if ingredient['units'] == 'g':
        # perform scaling
        for nutrient, quantity in nutrition.items():
            nutrition[nutrient] = quantity
        return nutrition
    if ingredient['units'] == 'ml':
        # convert to grams based on density
        for nutrient, quantity in nutrition.items():
            nutrition[nutrient] = quantity
        return nutrition
    raise Exception(f"Unknown unit type: {ingredient['units']}")


def parse_descriptions(descriptions):
    ingredients_by_product = {}
    for description in descriptions:
        try:
            ingredient = parse_description(description)
        except Exception as e:
            raise Exception(f'Parsing failed: "{description}" - {e}')
        product = ingredient['product']['product']
        ingredients_by_product[product] = ingredient
    return ingredients_by_product


def retrieve_knowledge(ingredients_by_product):
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
            ingredient['nutrition'] = determine_nutritional_content(ingredient)

            # TODO: Remove this remapping once the database handles native IDs
            if 'id' in ingredient['product']:
                ingredient['product']['product_id'] = \
                    ingredient['product'].pop('id')

    for product, ingredient in ingredients_by_product.items():
        ingredients_by_product[product]['description'] = product
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

    ingredients_by_product = parse_descriptions(descriptions)
    ingredients = retrieve_knowledge(ingredients_by_product)

    return jsonify(ingredients)
