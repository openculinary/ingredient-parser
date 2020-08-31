import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape


def inner_xml(element):
    return escape(element.text or '') + ''.join([
        ET.tostring(subelement, 'unicode')
        for subelement in element
    ])


def render(ingredient):
    markup = ingredient['markup']
    magnitude = ingredient.get('magnitude')
    units = ingredient.get('units')

    doc = ET.fromstring(f'<root>{markup}</root>')
    for element in doc.iter('mark'):
        element.tag = 'ingredient'
    doc = inner_xml(doc)

    amt = f'<qty>{magnitude}</qty>' if magnitude else ''
    amt += f'<unit>{units}</unit>' if units else ''
    amt = f'<amt>{amt}</amt>' if amt else ''

    return amt + doc
