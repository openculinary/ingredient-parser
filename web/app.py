from flask import Flask, jsonify, request
import httpx
from pint import UnitRegistry

from ingreedypy import Ingreedy

from web.recipeml import render, wrap


app = Flask(__name__)
pint = UnitRegistry()


def generate_subtexts(description):
    yield description
    if "/" in description:
        pre_text, post_text = description.split("/", 1)
        post_tokens = post_text.split(" ")
        if pre_text:
            yield "{} {}".format(pre_text, " ".join(post_tokens[1:]))
        yield " ".join(post_tokens)
    yield description.replace(",", "")


def parse_quantity(quantity):
    # Workaround: pint treats 'pinch' as 'pico-inch'
    # https://github.com/hgrecco/pint/issues/273
    if quantity["unit"] == "pinch":
        quantity["unit"] = "g"
        quantity["amount"] = (quantity.get("amount") or 1) * 0.35

    quantity = pint.Quantity(quantity["amount"], quantity["unit"])
    base_units = get_base_units(quantity) or quantity.units
    return quantity.to(base_units)


def parse_quantities(ingredient):
    parser = "ingreedypy"
    quantities = ingredient.get("quantity") or []
    if not quantities:
        return None, None, parser

    total = 0
    for quantity in quantities:
        try:
            total += parse_quantity(quantity)
            parser = "ingreedypy+pint"
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
        ingredient = Ingreedy().parse(text)
        product = ingredient.get("ingredient")
        if not product:
            continue
        product_parser = "ingreedypy"
        magnitude, units, parser = parse_quantities(ingredient)
        break

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


def determine_relative_density(ingredient):
    if ingredient.get("units") != "ml":
        return None
    product = ingredient["product"]["product"]
    if "flour" in product:
        return 0.593
    elif "sugar" in product:
        return 0.850
    elif "milk" in product:
        return 1.030
    elif "cream" in product:
        return 1.010
    elif "oil" in product:
        return 0.900
    elif "butter" in product:
        return 0.911
    return 1.0


def determine_nutritional_content(ingredient):
    nutrition = ingredient["product"].pop("nutrition", None)
    if not nutrition:
        return None
    if not ingredient.get("magnitude"):
        return None
    if not ingredient.get("units"):
        return None

    if ingredient["units"] == "g":
        grams = ingredient["magnitude"]
    elif ingredient["units"] == "ml":
        # convert to grams based on density
        grams = ingredient["magnitude"] * ingredient["relative_density"]
    else:
        raise Exception(f"Unknown unit type: {ingredient['units']}")

    results = {}
    nutrient_units = {"energy": "cal"}
    for nutrient, quantity in nutrition.items():
        quantity = quantity or 0
        ratio = grams / 100.0
        scaled_quantity = quantity * ratio
        results[f"{nutrient}"] = round(scaled_quantity, 2)
        results[f"{nutrient}_units"] = nutrient_units.get(nutrient, "g")
    return results


def parse_descriptions(descriptions):
    ingredients_by_product = {}
    for description in descriptions:
        try:
            ingredient = parse_description(description)
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


def attach_nutrition(ingredients):
    for ingredient in ingredients.values():
        ingredient["relative_density"] = determine_relative_density(ingredient)
        ingredient["nutrition"] = determine_nutritional_content(ingredient)
    return ingredients


def attach_markup(ingredients):
    for product, ingredient in ingredients.items():
        ingredients[product]["markup"] = render(ingredient)
    return list(ingredients.values())


@app.route("/", methods=["POST"])
def root():
    descriptions = request.form.getlist("descriptions[]")
    descriptions = [d.strip() for d in descriptions]

    ingredients_by_product = parse_descriptions(descriptions)
    ingredients = retrieve_knowledge(ingredients_by_product)
    ingredients = attach_nutrition(ingredients)
    ingredients = attach_markup(ingredients)

    return jsonify(ingredients)
