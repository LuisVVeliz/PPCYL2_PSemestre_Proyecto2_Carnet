import xml.etree.ElementTree as ET

def leer_xml(ruta):

    tree = ET.parse(ruta)
    root = tree.getroot()

    datos = []

    for elemento in root:
        datos.append(elemento.text)

    return datos