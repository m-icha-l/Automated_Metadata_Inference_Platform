"""
Adapters between the Django skeleton (services.py) and the engine (api/metadata_engine/).

services.py imports infer, to_xml and validate_xml from here. Engine imports are done
inside the functions, so a missing engine library breaks only that step and not the whole API.
"""
import tempfile
from datetime import date
from pathlib import Path

# True: build the XML with Kalle's mapper (iso_mapping.py), which is the path
# the engine's author has tested. False: use api/mcf.py (covers temporal extent, topic
# category, lineage and thesaurus keywords, but is not yet tested against the XSD).
USE_ENGINE_MAPPER = True

# Engine fields our record has no value for. FILL THESE FROM THE ENGINE'S WORKING
# SAMPLE (filled_example.json); empty values may be rejected by the XSD.
ENGINE_DEFAULTS = {
    "language": "en",
    "charset": "utf8",
    "hierarchylevel": "dataset",
    "identification_language": "en",
    "status": "completed",
    "datatype": "",
    "geomtype": "",
    "rights": "",
    "url": "",
    "author_organization": "",
    "author_individualname": "",
    "author_email": "",
    "author_role": "",
    "contact_organization": "",
    "contact_individualname": "",
    "contact_role": "",
    "format": "",
    "format_version": "",
    "distribution_description": "",
}

# engine field -> our record field, for plain values
SIMPLE_FIELDS = {
    "title": "title",
    "abstract": "abstract",
    "crs": "crs",
    "contact_email": "contact_email",
}


def _value(raw: dict, key: str):
    """The engine reports every field as {"value": ..., "status": "inferred"|"missing"|...}.
    Returns the value, or None if the field is missing or empty."""
    item = raw.get(key)
    if not isinstance(item, dict) or item.get("status") == "missing":
        return None
    value = item.get("value")
    return None if value in ("", [], {}, None) else value


def engine_to_record(raw: dict) -> dict:
    """Engine output -> our record format (serializers.MetadataContentSerializer).
    Only fields the engine actually found are included; the rest become gaps."""
    record = {}

    for theirs, ours in SIMPLE_FIELDS.items():
        value = _value(raw, theirs)
        if value is not None:
            record[ours] = value

    keywords = _value(raw, "keywords")
    if keywords:
        record["keywords"] = [{"keyword": str(k)} for k in keywords]

    # ASSUMPTION TO CONFIRM: bbox is [west, south, east, north] in WGS84 degrees.
    bbox = _value(raw, "bbox")
    if bbox and len(bbox) == 4:
        record["bounding_box_bbox"] = [float(x) for x in bbox]

    # The engine reports statistics per band; we store one set (band 1).
    bands = _value(raw, "band_statistics")
    if bands:
        first = bands[0]
        record["statistics"] = {
            key: (float(first[key]) if first.get(key) is not None else None)
            for key in ("min", "max", "mean", "nodata")
        }

    return record


def infer(path: str, ext: str) -> dict:
    """TASK 1: run the engine's inference and convert the result to our record format."""
    from .services import UnreadableFile            # imported late to avoid a circular import
    from .metadata_engine.inference import infer_metadata

    try:
        raw = infer_metadata(path)
    except (ValueError, RuntimeError) as e:         # engine: unsupported format; GDAL: unreadable file
        raise UnreadableFile(str(e))
    return engine_to_record(raw)


def _record_to_engine(record: dict) -> dict:
    """Our record -> the engine's flat {key: {"value": ...}} input for iso_mapping.map_iso_metadata."""
    distribution = record.get("distribution") or {}
    today = date.today().isoformat()
    flat = dict(ENGINE_DEFAULTS)
    flat.update({
        "identifier": distribution.get("identifier", ""),
        "metadata_creation": today,
        "title": record.get("title", ""),
        "abstract": record.get("abstract", ""),
        "identification_creation": record.get("dataset_date") or today,  # placeholder date
        "keywords": [k["keyword"] for k in record.get("keywords") or []],
        # Our bbox is always WGS84, so the extent's CRS is 4326 whatever the dataset's own CRS is.
        "crs": 4326,
        "bbox": list(record.get("bounding_box_bbox") or []),
        "contact_email": record.get("contact_email", ""),
        "distribution_url": distribution.get("access_url", ""),
        "distribution_type": "WWW:LINK",
        "distribution_name": record.get("title", ""),
        "distribution_function": "download",
    })
    return {key: {"value": value} for key, value in flat.items()}


def to_xml(record: dict) -> str:
    """TASK 5: our record -> ISO 19139 XML string via the engine's xml_generation."""
    if USE_ENGINE_MAPPER:
        from .metadata_engine.xml_generation import generate_iso19139_from_dict
        return generate_iso19139_from_dict(_record_to_engine(record))

    # Alternative path (off by default): our own record -> MCF mapping in mcf.py.
    import yaml
    from pygeometa.core import read_mcf
    from pygeometa.schemas.iso19139 import ISO19139OutputSchema
    from .mcf import record_to_mcf

    yml = yaml.safe_dump(record_to_mcf(record), sort_keys=False)
    return ISO19139OutputSchema().write(read_mcf(yml))


def validate_xml(xml: str) -> list:
    """TASK 5: validate with the engine's XSD check. Returns a list of error strings.
    The engine returns (is_valid, [(message, line), ...])."""
    from .metadata_engine.xml_validation import validate_iso19139

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "record.xml"
        path.write_text(xml, encoding="utf-8")
        is_valid, errors = validate_iso19139(str(path))

    if is_valid:
        return []
    return [f"line {line}: {message}" if line else str(message) for message, line in errors]
