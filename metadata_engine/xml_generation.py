import json
from pathlib import Path
from pygeometa.core import read_mcf
from pygeometa.schemas.iso19139 import ISO19139OutputSchema
from iso_mapping import map_iso_metadata


def generate_iso19139(json_file):

    with open(json_file, "r", encoding="utf-8") as f:
        extracted = json.load(f)

    yml = map_iso_metadata(extracted)

    # read from string
    mcf_dict = read_mcf(yml)

    # choose ISO 19139 output schema
    iso_os = ISO19139OutputSchema()

    # default schema
    xml_string = iso_os.write(mcf_dict)

    return xml_string


if __name__ == "__main__":
    input_file = Path("generated_json/filled_example.json")

    xml_string = generate_iso19139(input_file)

    output = Path("generated_xml/filled_example.xml")
    output.write_text(xml_string, encoding="UTF-8")

    print("ISO 19139 XML generated!")