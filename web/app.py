from flask import Flask, jsonify, request
from fractions import Fraction
import json
from unicodedata import numeric
from subprocess import Popen, PIPE

from ingreedypy import Ingreedy


app = Flask(__name__)


def parse_nyt(ingredients):
    env = {
        'PATH': '/usr/bin:/usr/local/bin',
        'PYTHONPATH': '..'
    }
    command = [
        'bin/parse-ingredients.py',
        '--model-file',
        'model/20191009_1221-nyt-ingredients-snapshot-2015-91bf5a6.crfmodel',
    ]
    parser = Popen(command, env=env, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out, err = parser.communicate('\n'.join(ingredients))
    return json.loads(out)


def parse_ingreedypy(ingredient):
    try:
        result = Ingreedy().parse(ingredient)
    except Exception as e:
        try:
            result = Ingreedy().parse(ingredient[e.column():])
        except:
            return

    return {
        'parser': 'ingreedypy',
        'input': ingredient,
        'product': result.get('ingredient'),
        'quantity': result.get('amount'),
        'units': result.get('unit'),
    }


def merge_result_field(winner, field):
    if winner.get(field) is None:
        return {}

    nested_fields = {'product'}
    parser = '{}_parser'.format(field)
    result = {
        field: winner[field],
        parser: winner['parser'] if winner[field] else None,
    }
    return {field: result} if field in nested_fields else result


def merge_results(a, b):
    a_product = not b or a.get('product') and len(a['product']) <= len(b['product'])
    a_quantity = not b or a.get('quantity')
    a_units = not b or a.get('units')

    winners = {
        'product': a if a_product else b,
        'quantity': a if a_quantity else b,
        'units': a if a_units else b,
    }

    results = {'description': a['description']}
    for field in ['product', 'quantity', 'units']:
        winner = winners[field]
        result = merge_result_field(winner, field)
        results = dict(results.items() + result.items())
    return results


def parse_qty(value):
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
    except:
        return None


@app.route('/')
def root():
    ingredients = request.args.getlist('ingredients[]')
    ingredients = [ingredient.encode('utf-8') for ingredient in ingredients]
    ingredients = [ingredient.strip().lower() for ingredient in ingredients]

    nyt_results = parse_nyt(ingredients)
    nyt_results = [{
        'parser': 'nyt',
        'description': nyt_result['input'],
        'product': nyt_result.get('name'),
        'quantity': parse_qty(nyt_result.get('qty')),
        'units': nyt_result.get('unit'),
    } for nyt_result in nyt_results]

    results = {}
    for nyt_result in nyt_results:
        description = nyt_result['description']
        igy_result = parse_ingreedypy(description)
        results[description] = merge_results(nyt_result, igy_result)
    return jsonify(results)
