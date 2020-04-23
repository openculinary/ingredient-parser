import xml.etree.ElementTree as ET


def merge(ingredient_markup, quantity, units):
    print(ingredient_markup)
    doc = ET.fromstring(f'<root>{ingredient_markup}</root>')
    print(ET.tostring(doc))
    for element in doc.iter('mark'):
        element.tag = 'ingredient'
    return ET.tostring(doc)
