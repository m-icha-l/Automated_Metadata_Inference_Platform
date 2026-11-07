def map_iso_metadata(extracted):

    metadata = {

        "mcf": {
            "version": 2.0
        },

        "metadata": {
            "identifier": extracted["identifier"],
            "language": extracted["language"],
            "charset": extracted["charset"],
            "hierarchylevel": extracted["hierarchylevel"],
            "dates": {
                "creation": extracted["metadata_creation"]
            }
        },

        "spatial": {
            "datatype": extracted["datatype"],
            "geomtype": extracted["geomtype"]
        },

        "identification": {
            "title": extracted["title"],
            "abstract": extracted["abstract"],
            "language": extracted["identification_language"],
            "rights": extracted["rights"],
            "url": extracted["url"],
            "status": extracted["status"],
            "dates": {
                "creation": extracted["identification_creation"]
            },
            "keywords": {
                "default": {
                    "keywords": extracted["keywords"]
                }
            },
            "extents": {
                "spatial": [
                    {
                        "crs": extracted["crs"],
                        "bbox": extracted["bbox"]
                    }
                ]
            }
        },

        "contact": {
            "author": {
                "organization": extracted["author_organization"],
                "individualname": extracted["author_individualname"],
                "email": extracted["author_email"],
                "role": extracted["author_role"]
            },

            "pointOfContact": {
                "organization": extracted["contact_organization"],
                "individualname": extracted["contact_individualname"],
                "email": extracted["contact_email"],
                "role": extracted["contact_role"]
            }
        },

        "distribution": {
            "www": {
                "format": extracted["format"],
                "format_version": extracted["format_version"],
                "url": extracted["distribution_url"],
                "type": extracted["distribution_type"],
                "name": extracted["distribution_name"],
                "description": extracted["distribution_description"],
                "function": extracted["distribution_function"]
            }
        }
        
    }

    return metadata
