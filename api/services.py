"""
Service layer. Views call ONLY these functions, so the web form and the REST
API go through exactly the same inference, gap detection and validation.

Real here:  find_gaps, check_record (the gate that cannot be bypassed)
Connected:  infer, to_xml, validate_xml  -> engine_adapters.py (teammate's engine in metadata_engine/)
            assign_identifier            -> identifiers.py (task 6)
            store_record                 -> storage.py (task 8)

A "record" is a plain dict shaped like MetadataContentSerializer. Datetimes
are timezone-aware datetime objects.
"""
from dataclasses import dataclass, field

from rest_framework.exceptions import APIException

# Connected pieces. Engine libraries are only imported when a function runs
# (see engine_adapters.py), so a missing engine dependency cannot stop Django starting.
from .engine_adapters import infer, to_xml, validate_xml  # noqa: F401
from .identifiers import assign_identifier  # noqa: F401
from .storage import store_record  # noqa: F401


class NotYetImplemented(APIException):
    status_code = 501
    default_detail = "This part of the pipeline has not been implemented yet."
    default_code = "not_implemented"


class UnreadableFile(Exception):
    """Raised by infer() when the upload is corrupt or has no usable content."""


# Dotted paths. Single source of truth for gap detection: the form should ask the
# API for gaps rather than keep its own list.
REQUIRED_FIELDS = [
    "title", "abstract", "contact_email", "topic_category", "keywords",
    "lineage", "crs", "bounding_box_bbox",
    "temporal_extent.start", "temporal_extent.end", "temporal_extent.timezone",
]

# File types the engine accepts. No .shp: a shapefile needs several files, so it
# has to come in a zip, and zip handling is not implemented yet.
SUPPORTED_EXTENSIONS = {".geojson", ".json", ".kml", ".txt", ".xls", ".xlsx",
                        ".tif", ".tiff", ".asc", ".hdf", ".hdf5", ".nc"}


def _get(record: dict, path: str):
    cur = record
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
        if cur is None:
            return None
    return cur


def find_gaps(record: dict) -> list:
    return [p for p in REQUIRED_FIELDS if _get(record, p) in (None, "", [], {})]


@dataclass
class CheckResult:
    gaps: list = field(default_factory=list)
    schema_errors: list = field(default_factory=list)
    xml: str = None

    @property
    def is_valid(self) -> bool:
        return not self.gaps and not self.schema_errors


def check_record(record: dict) -> CheckResult:
    """Gap detection, then serialisation and XSD validation. Used by BOTH
    /validate/ and /submit/, so submission cannot skip either check."""
    gaps = find_gaps(record)
    if gaps:  # no point serialising an incomplete record
        return CheckResult(gaps=gaps)
    xml = to_xml(record)
    return CheckResult(schema_errors=validate_xml(xml), xml=xml)
