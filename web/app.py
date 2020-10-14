from flask import Flask, jsonify, request
from pint import UnitRegistry
import requests

from ingreedypy import Ingreedy

from web.recipeml import render


app = Flask(__name__)
pint = UnitRegistry()


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

    quantity = pint.Quantity(quantity['amount'], quantity['unit'])
    base_units = get_base_units(quantity) or quantity.units
    return quantity.to(base_units)


def parse_quantities(ingredient):
    parser = 'ingreedypy'
    quantities = ingredient.get('quantity') or []
    if not quantities:
        return None, None, parser

    total = 0
    for quantity in quantities:
        try:
            total += parse_quantity(quantity)
            parser = 'ingreedypy+pint'
        except Exception:
            return None, None, parser
    if not total > 0:
        return None, None, parser

    magnitude = round(total.magnitude, 2)
    units = None if total.dimensionless else pint.get_symbol(str(total.units))
    return magnitude, units, parser


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


def determine_relative_density(ingredient):
    product = ingredient['product']['product']
    if 'flour' in product:
        return 0.593
    elif 'sugar' in product:
        return 0.850
    elif 'milk' in product:
        return 1.030
    elif 'cream' in product:
        return 1.010
    elif 'oil' in product:
        return 0.900
    elif 'butter' in product:
        return 0.911
    return 1.0


def determine_nutritional_content(ingredient):
    nutrition = ingredient['product'].pop('nutrition', None)
    if not nutrition:
        return None
    if not ingredient.get('magnitude'):
        return None
    if not ingredient.get('units'):
        return None

    if ingredient['units'] == 'g':
        grams = ingredient['magnitude']
    elif ingredient['units'] == 'ml':
        # convert to grams based on density
        ratio = determine_relative_density(ingredient)
        grams = ingredient['magnitude'] * ratio
    else:
        raise Exception(f"Unknown unit type: {ingredient['units']}")

    for nutrient, quantity in nutrition.items():
        quantity = quantity or 0
        ratio = grams / 100.0
        scaled_quantity = quantity * ratio
        nutrition[nutrient] = round(scaled_quantity, 2)
    return nutrition


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
    response = requests.post(
        url='http://knowledge-graph-service/ingredients/query',
        data={'descriptions[]': list(ingredients_by_product.keys())},
        proxies={}
    )
    knowledge = response.json()['results'] if response.ok else {}
    for product in knowledge.keys():
        if knowledge[product]['product'] is None:
            continue
        ingredient = ingredients_by_product[product]
        ingredient['markup'] = knowledge[product]['query']['markup']
        ingredient['product'] = knowledge[product]['product']
        ingredient['product']['product_parser'] = 'knowledge-graph'
        ingredient['nutrition'] = determine_nutritional_content(ingredient)

        # TODO: Remove this remapping once the database handles native IDs
        if 'id' in ingredient['product']:
            ingredient['product']['product_id'] = \
                ingredient['product'].pop('id')
    return ingredients_by_product


def get_base_units(quantity):
    dimensionalities = {
        None: pint.Quantity(1),
        'length': pint.Quantity(1, 'cm'),
        'volume': pint.Quantity(1, 'ml'),
        'weight': pint.Quantity(1, 'g'),
    }
    dimensionalities = {
        v.dimensionality: pint.get_symbol(str(v.units)) if k else None
        for k, v in dimensionalities.items()
    }
    return dimensionalities.get(quantity.dimensionality)


def attach_markup(ingredients):
    for product, ingredient in ingredients.items():
        ingredients[product]['markup'] = render(ingredient)
    return list(ingredients.values())


@app.route('/', methods=['POST'])
def root():
    descriptions = request.form.getlist('descriptions[]')
    descriptions = [d.strip() for d in descriptions]

    ingredients_by_product = parse_descriptions(descriptions)
    ingredients = retrieve_knowledge(ingredients_by_product)
    ingredients = attach_markup(ingredients)

    return jsonify(ingredients)
