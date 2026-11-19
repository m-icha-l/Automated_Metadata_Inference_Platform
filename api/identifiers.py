"""
Task 6: persistent identifier and data access URL.

The mechanism (DOI, Handle, URN, ...) is still to be decided with the DIWA team.
Until then: a random, collision-free identifier, and an access URL built from the
Allas public-bucket URL scheme (https://a3s.fi/<bucket>/<object>) as a stand-in.

To switch mechanism later, only this file should need to change.
In services.py:  from .identifiers import assign_identifier  # noqa: F401
"""
import uuid

from django.conf import settings


def assign_identifier(record: dict) -> dict:
    """Return {"identifier": ..., "access_url": ...} for a record being submitted.

    Idempotent: a record that already has distribution info keeps it, so a later
    new version of the same record can keep its identifier.
    """
    existing = record.get("distribution")
    if existing:
        return dict(existing)

    token = uuid.uuid4()
    prefix = getattr(settings, "DIWA_IDENTIFIER_PREFIX", "diwa:")
    base = getattr(settings, "DIWA_DATA_BASE_URL", "https://a3s.fi/CHANGE-ME-bucket").rstrip("/")
    object_name = getattr(settings, "DIWA_DATA_OBJECT_NAME", "data.zip")

    return {
        "identifier": f"{prefix}{token}",
        # The uploader must store the data file under exactly this object key.
        "access_url": f"{base}/{token}/{object_name}",
    }