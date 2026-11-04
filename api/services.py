"""
Service layer. Views call ONLY these functions, so the web form and the REST
API go through exactly the same inference, gap detection and validation.

Real:  find_gaps, check_record, store_record (via storage.py)
Stubs: infer, to_xml, validate_xml, assign_identifier. They raise
       NotYetImplemented (HTTP 501) rather than returning fake data.

A "record" is a plain dict shaped like MetadataContentSerializer. Datetimes
are timezone-aware datetime objects.
"""
from dataclasses import dataclass, field

from rest_framework.exceptions import APIException

from .storage import store_record  # noqa: F401  (task 8, implemented)


class NotYetImplemented(APIException):
    status_code = 501
    default_detail = "This part of the pipeline has not been implemented yet."
    default_code = "not_implemented"


class UnreadableFile(Exception):
    """Raised by infer() when the upload is corrupt or has no usable content."""


REQUIRED_FIELDS = [
    "title", "abstract", "contact_email", "topic_category", "keywords",
    "lineage", "crs", "bounding_box_bbox",
    "temporal_extent.start", "temporal_extent.end", "temporal_extent.timezone",
]

# Owned by task 1. Includes .zip (mixed contents) and images (EXIF).
SUPPORTED_EXTENSIONS = {
    ".zip", ".tif", ".tiff", ".geojson", ".json", ".gpkg", ".jpg", ".jpeg",
}


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
    if gaps:
        return CheckResult(gaps=gaps)
    xml = to_xml(record)
    return CheckResult(schema_errors=validate_xml(xml), xml=xml)


# ---- STUBS (owned by other tasks) ----------------------------------------
def infer(path: str, ext: str) -> dict:
    """TASK 1. Return a draft record dict; raise UnreadableFile for corrupt input."""
    raise NotYetImplemented()


def to_xml(record: dict) -> str:
    """TASK 5. Serialise to ISO 19139 XML via pygeometa."""
    raise NotYetImplemented()


def validate_xml(xml: str) -> list:
    """TASK 5. Return a list of error strings (empty = valid)."""
    raise NotYetImplemented()


def assign_identifier(record: dict) -> dict:
    """TASK 6. Return {"identifier": ..., "access_url": ...}."""
    raise NotYetImplemented()