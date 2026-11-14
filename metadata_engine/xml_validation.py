from pathlib import Path
from lxml import etree

BASE_FOLDER = Path(__file__).parent
SCHEMA_FOLDER = BASE_FOLDER / "schemas"

class LocalSchemaResolver(etree.Resolver):

    def resolve(self, url, public_id, context):

        schemas = { "http://schemas.opengis.net/iso/19139/20070417/": SCHEMA_FOLDER / "iso_19139",
                    "https://schemas.opengis.net/iso/19139/20070417/": SCHEMA_FOLDER / "iso_19139",
                    "http://schemas.opengis.net/gml/3.2.1/": SCHEMA_FOLDER / "gml" / "3.2.1.2",
                    "http://www.w3.org/1999/xlink.xsd": SCHEMA_FOLDER / "xlink" / "xlink.xsd",
                    "http://www.w3.org/2001/xml.xsd": SCHEMA_FOLDER / "xml" / "xml.xsd"}

        for url_start, folder in schemas.items():

            if url.startswith(url_start):
                file_name = url[len(url_start):]
                local_file = folder / file_name
                if local_file.is_file():
                    return self.resolve_filename(str(local_file), context)

                raise OSError(f"Schema file not found: {local_file}")

        return None


def validate_iso19139(xml_file):

    xsd_file = (SCHEMA_FOLDER / "iso_19139" / "gmx" / "gmx.xsd")
    
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    parser.resolvers.add(LocalSchemaResolver())

    try:
        xml = etree.parse(str(xml_file), parser)
        xsd = etree.parse(str(xsd_file), parser)

        schema = etree.XMLSchema(xsd)
        schema.assertValid(xml)

        return True, []

    # Error when xml document does not follow xml schema
    except etree.DocumentInvalid as error:
        errors = []
        for entry in error.error_log:
            message = entry.message
            line = entry.line
            errors.append((message, line))
        return False, errors

    except (etree.XMLSyntaxError, etree.XMLSchemaParseError, OSError) as error:
        return False, [(str(error), None)]


if __name__ == "__main__":

    xml_file = BASE_FOLDER / "generated_xml" / "filled_example.xml"
    valid, errors = validate_iso19139(xml_file)

    if valid:
        print("XML is valid against ISO 19139!")
    else:
        print("XML validation failed:")

        for message, line in errors:
            print(f"Line {line}: {message}")
