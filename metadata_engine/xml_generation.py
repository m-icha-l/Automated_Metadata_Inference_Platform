from pathlib import Path
from pygeometa.core import read_mcf
from pygeometa.schemas.iso19139 import ISO19139OutputSchema


def generate_iso19139(yml, output):

    # read from string
    mcf_dict = read_mcf(yml)

    # choose ISO 19139 output schema
    iso_os = ISO19139OutputSchema()

    # default schema
    xml_string = iso_os.write(mcf_dict)

    # write to disk
    Path(output).write_text(xml_string, encoding="UTF-8")

    return output


if __name__ == "__main__":
    generate_iso19139("yml_samples/empty_sample.yml", "generated_xml/empty_sample.xml")
    print("ISO 19139 XML generated.(empty sample)")
