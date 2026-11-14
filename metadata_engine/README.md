
# Metadata Engine

## 1. How It Works

The Metadata Engine processes geospatial datasets in two stages.

**Stage 1: Metadata Extraction**

1. The user uploaded file is read using `inference.py`.
2. `inference.py` calls `metadata_extraction.py` to extract available metadata.
3. The extracted metadata is converted to json file which contains information about ISO fields(see metadata_engine/json to see an example).

**Stage 2: ISO 19139 XML Generation and validation**

1. `iso_mapping.py` maps the metadata into an ISO structure and generates YAML.
2. `xml_generation.py` calls `iso_mapping` and converts the mapped metadata YAML file into ISO 19139 XML 
3. `xml_validation.py` validates the XML against the XSD schemas.

## 2. How use it
1. In `inference.py` use `infer_metadata(file_path)` to make report about inferred fields. Returns json.
2. In `xml_generation.py` use `validate_iso19139(xml_file)` to generate a xml file from a json file. Returns xml.
3. In `xml_validation.py` use `generate_iso19139(json_file)` to validate xml. Returns true if valid.

## 3. Files and Folders

### Python Files

| File | Purpose | Status |
|---|---|---|
| `__init__.py` | Makes the engine directory a Python package. | 
| `inference.py` | Coordinates metadata extraction. | Works |
| `metadata_extraction.py` | Extracts metadata from different geospatial files | Works, but not fully implemented |
| `iso_mapping.py` | Maps completed metadata into an ISO structure and generates YAML. | Works |
| `xml_generation.py` | Generates ISO 19139 XML from the mapped metadata. | Works |
| `xml_validation.py` | Validates XML against XSD schemas. | Works |
| `tests.py` | Contains tests for the engine. | Not implemented |

### Folders

| Folder | Purpose |
|---|---|
| `schemas/` | Stores XSD files used for XML validation. |
| `yml_samples/` | Stores sample yml files for testing. |
| `json/` | Stores generated json files for testing. |
| `generated_xml/` | Stores generated ISO 19139 XML files for testing. |

