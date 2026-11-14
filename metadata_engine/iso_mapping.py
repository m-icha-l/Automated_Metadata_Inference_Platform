import json
import yaml
from pathlib import Path

def map_iso_metadata(json_file):

    def get_value(key):
        return json_file.get(key, {}).get("value", "")    

    metadata = {
        "mcf": {
            "version": 2.0
        },
        "metadata": {
            "identifier": get_value("identifier"),
            "language": get_value("language"),
            "charset": get_value("charset"),
            "hierarchylevel": get_value("hierarchylevel"),
            "dates": {
                "creation": get_value("metadata_creation")
            }
        },
        "spatial": {
            "datatype": get_value("datatype"),
            "geomtype": get_value("geomtype")
        },
        "identification": {
            "title": get_value("title"),
            "abstract": get_value("abstract"),
            "language": get_value("identification_language"),
            "rights": get_value("rights"),
            "url": get_value("url"),
            "status": get_value("status"),
            "dates": {
                "creation": get_value("identification_creation")
            },
            "keywords": {
                "default": {
                    "keywords": get_value("keywords")
                }
            },
            "extents": {
                "spatial": [
                    {
                        "crs": get_value("crs"),
                        "bbox": get_value("bbox")
                    }
                ]
            }
        },
        "contact": {
            "author": {
                "organization": get_value("author_organization"),
                "individualname": get_value("author_individualname"),
                "email": get_value("author_email"),
                "role": get_value("author_role")
            },
            "pointOfContact": {
                "organization": get_value("contact_organization"),
                "individualname": get_value("contact_individualname"),
                "email": get_value("contact_email"),
                "role": get_value("contact_role")
            }
        },
        "distribution": {
            "www": {
                "format": get_value("format"),
                "format_version": get_value("format_version"),
                "url": get_value("distribution_url"),
                "type": get_value("distribution_type"),
                "name": get_value("distribution_name"),
                "description": get_value("distribution_description"),
                "function": get_value("distribution_function")
            }
        }
    }

    yml = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True, default_flow_style=False)

    return yml


if __name__ == "__main__":

    base_dir = Path(__file__).resolve().parent
    input_file = base_dir / "generated_json" / "filled_example.json"

    with open(input_file, "r", encoding="utf-8") as f:
        extracted = json.load(f)

    yml = map_iso_metadata(extracted)

    output_file = base_dir / "yml_samples" / "filled_example.yml"
    output_file.write_text(yml, encoding="utf-8")

    print("\nGenerated YAML:\n")
    print(yml)