import xml.etree.ElementTree as ET


def inner_xml(element):
    return (element.text or '') + ''.join([
        ET.tostring(subelement, 'unicode')
        for subelement in element
    ])


def merge(ingredient_markup, quantity, units):
    ingredient = ET.fromstring(f'<root>{ingredient_markup}</root>')
    for element in ingredient.iter('mark'):
        element.tag = 'ingredient'
    ingredient = inner_xml(ingredient)

    amt = f'<qty>{quantity}</qty>' if quantity else ''
    amt += f'<unit>{units}</unit>' if units else ''
    amt = f'<amt>{amt}</amt>' if amt else ''

    return amt + ingredient
