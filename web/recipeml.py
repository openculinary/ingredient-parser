import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape


def inner_xml(element):
    return escape(element.text or '') + ''.join([
        ET.tostring(subelement, 'unicode')
        for subelement in element
    ])


def merge(ingredient_markup, magnitude, units):
    ingredient = ET.fromstring(f'<root>{ingredient_markup}</root>')
    for element in ingredient.iter('mark'):
        element.tag = 'ingredient'
    ingredient = inner_xml(ingredient)

    amt = f'<qty>{magnitude}</qty>' if magnitude else ''
    amt += f'<unit>{units}</unit>' if units else ''
    amt = f'<amt>{amt}</amt>' if amt else ''

    return amt + ingredient
