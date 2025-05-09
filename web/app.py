from flask import Flask, jsonify, request
import httpx
from pint import UnitRegistry

from ingreedypy import Ingreedy

from web.recipeml import render, wrap


app = Flask(__name__)
pint = UnitRegistry()


def generate_subtexts(language_code, description):
    yield description
    if "/" in description:
        pre_text, post_text = description.split("/", 1)
        post_tokens = post_text.split(" ")
        if pre_text:
            yield "{} {}".format(pre_text, " ".join(post_tokens[1:]))
        yield " ".join(post_tokens)
    yield description.replace(",", "")


def parse_quantity(language_code, quantity):
    # Workaround: pint treats 'pinch' as 'pico-inch'
    # https://github.com/hgrecco/pint/issues/273
    if quantity["unit"] == "pinch":
        quantity["unit"] = "g"
        quantity["amount"] = (quantity.get("amount") or 1) * 0.35

    quantity = pint.Quantity(quantity["amount"], quantity["unit"])
    base_units = get_base_units(quantity) or quantity.units
    return quantity.to(base_units)


def parse_quantities(language_code, ingredient):
    parser = "ingreedypy"
    quantities = ingredient.get("quantity") or []
    if not quantities:
        return None, None, parser

    total = 0
    for quantity in quantities:
        try:
            total += parse_quantity(language_code, quantity)
            parser = "ingreedypy+pint"
        except Exception:
            return None, None, parser
    if not total > 0:
        return None, None, parser

    magnitude = round(total.magnitude, 2)
    units = None if total.dimensionless else pint.get_symbol(str(total.units))
    return magnitude, units, parser


def parse_description(language_code, description):
    product = description
    product_parser = None
    magnitude = None
    units = None
    parser = None

    for text in generate_subtexts(language_code, description):
        ingredient = Ingreedy().parse(text)
        product = ingredient.get("ingredient")
        if not product:
            continue
        product_parser = "ingreedypy"
        magnitude, units, parser = parse_quantities(language_code, ingredient)
        break

    if not product:
        msg = f"Unable to identify a product from ingredient description {description}"
        raise ValueError(msg)

    return {
        "description": description,
        "product": {
            "id": None,
            "product": product,
            "product_parser": product_parser,
        },
        "markup": wrap(product),
        "magnitude": magnitude,
        "magnitude_parser": parser,
        "units": units,
        "units_parser": parser,
    }


def parse_descriptions(language_code, descriptions):
    ingredients_by_product = {}
    for description in descriptions:
        try:
            ingredient = parse_description(language_code, description)
        except Exception as e:
            raise Exception(f'Parsing failed: "{description}" - {e}')
        product = ingredient["product"]["product"]
        ingredients_by_product[product] = ingredient
    return ingredients_by_product


def retrieve_knowledge(ingredients_by_product):
    response = httpx.post(
        url="http://knowledge-graph-service/ingredients/query",
        data={"descriptions[]": list(ingredients_by_product.keys())},
        proxy=None,
    )
    knowledge = response.json()["results"] if response.is_success else {}
    for product in knowledge.keys():
        if knowledge[product]["product"] is None:
            continue
        ingredient = ingredients_by_product[product]
        ingredient["markup"] = knowledge[product]["query"]["markup"]
        ingredient["product"] = knowledge[product]["product"]
        ingredient["product"]["product_parser"] = "knowledge-graph"
    return ingredients_by_product


def get_base_units(quantity):
    dimensionalities = {
        None: pint.Quantity(1),
        "length": pint.Quantity(1, "cm"),
        "volume": pint.Quantity(1, "ml"),
        "weight": pint.Quantity(1, "g"),
    }
    dimensionalities = {
        v.dimensionality: pint.get_symbol(str(v.units)) if k else None
        for k, v in dimensionalities.items()
    }
    return dimensionalities.get(quantity.dimensionality)


def attach_markup(ingredients):
    for product, ingredient in ingredients.items():
        ingredients[product]["markup"] = render(ingredient)
    return list(ingredients.values())


@app.route("/", methods=["POST"])
def root():
    language_code = request.form.get("language_code", type=str, default="en")
    descriptions = request.form.getlist("descriptions[]")
    descriptions = [d.strip() for d in descriptions]

    ingredients_by_product = parse_descriptions(language_code, descriptions)
    ingredients = retrieve_knowledge(ingredients_by_product)
    ingredients = attach_markup(ingredients)

    return jsonify(ingredients)
