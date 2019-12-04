from flask import Flask, jsonify, request
from fractions import Fraction
import json
from pint import UnitRegistry
import re
from unicodedata import numeric
from subprocess import Popen, PIPE

from ingreedypy import Ingreedy


app = Flask(__name__)
unit_registry = UnitRegistry()


def parse_descriptions_nyt(descriptions):
    env = {'PATH': '/usr/bin:/usr/local/bin', 'PYTHONPATH': '..'}
    command = ['bin/parse-ingredients.py', '--model-file', 'model/latest']
    parser = Popen(command, env=env, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out, err = parser.communicate('\n'.join(descriptions))
    return json.loads(out)


def generate_subtexts(description):
    yield description
    if '/' in description:
        pre_text, post_text = description.split('/', 1)
        post_tokens = post_text.split(' ')
        if pre_text:
            yield u'{} {}'.format(pre_text, u' '.join(post_tokens[1:]))
        yield u' '.join(post_tokens)
    yield description.replace(',', '')


def parse_description_ingreedypy(description):
    ingreedy = Ingreedy()
    ingredient = {}
    for text in generate_subtexts(description):
        try:
            ingredient = ingreedy.parse(text)
            break
        except Exception:
            pass

    return {
        'parser': 'ingreedypy',
        'description': description,
        'product': ingredient.get('ingredient'),
        'quantity': ingredient.get('amount'),
        'units': ingredient.get('unit'),
    }


def parse_quantity(value):
    if value is None:
        return

    try:
        quantity = 0
        fragments = value.split()
        for fragment in fragments:
            if len(fragment) == 1:
                fragment = numeric(fragment)
            elif fragment[-1].isdigit():
                fragment = Fraction(fragment)
            else:
                fragment = Fraction(fragment[:-1]) + numeric(fragment[-1])
            quantity += float(fragment)
        return quantity
    except Exception:
        return None


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

    result = {
        'quantity': round(quantity.magnitude, 2),
        'quantity_parser': ingredient['parser'] + '+pint'
    }
    result.update({
        'units': base_units,
        'units_parser': ingredient['parser'] + '+pint'
    } if base_units else {})
    return result


def merge_ingredient_field(winner, field):
    if winner.get(field) is None:
        return {}

    nested_fields = {'product'}
    parser = '{}_parser'.format(field)
    ingredient = {
        field: winner[field],
        parser: winner['parser'] if winner[field] else None,
    }
    return {field: ingredient} if field in nested_fields else ingredient


def contains(item, field):
    if not item:
        return False
    return item.get(field) is not None


def merge_ingredients(a, b):
    description = (a or b).get('description')
    a_product = (
        not contains(b, 'product') or contains(a, 'product')
        and len(a['product']) <= len(b['product'])
    )
    a_quantity = (
        not contains(b, 'quantity') or contains(a, 'quantity')
        and a['quantity'] in re.findall('\\d+', description)
        and not b['quantity'] in re.findall('\\d+', description)
    )

    winners = {
        'product': a if a_product else b,
        'quantity': a if a_quantity else b,
        'units': a if a_quantity else b,
    }

    ingredient = {
        'description': description,
        'parsers': {v['parser']: v for v in [a, b] if v}
    }
    for field in ['product', 'quantity', 'units']:
        winner = winners[field]
        merge_field = merge_ingredient_field(winner, field)
        ingredient.update(merge_field)

    units_field = parse_units(a if a_quantity else b)
    if not units_field:
        units_field = parse_units(b if a_quantity else a)
    if units_field:
        ingredient.update(units_field)

    return ingredient


@app.route('/', methods=['POST'])
def root():
    descriptions = request.form.getlist('descriptions[]')
    descriptions = [d.encode('utf-8') for d in descriptions]
    descriptions = [d.strip().lower() for d in descriptions]

    nyt_ingredients = parse_descriptions_nyt(descriptions)
    nyt_ingredients = [{
        'parser': 'nyt',
        'description': nyt_ingredient['input'],
        'product': nyt_ingredient.get('name'),
        'quantity': parse_quantity(nyt_ingredient.get('qty')),
        'units': nyt_ingredient.get('unit'),
    } for nyt_ingredient in nyt_ingredients]

    ingredients = []
    for nyt_ingredient in nyt_ingredients:
        description = nyt_ingredient['description']
        igy_ingredient = parse_description_ingreedypy(description)
        ingredient = merge_ingredients(nyt_ingredient, igy_ingredient)
        ingredients.append(ingredient)
    return jsonify(ingredients)
