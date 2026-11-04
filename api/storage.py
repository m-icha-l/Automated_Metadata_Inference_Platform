"""
Task 8 implementation of the store_record contract from services.py.
"""
from django.contrib.gis.geos import Polygon
from django.db import transaction

from .models import MetadataRecord, QAQCAudit, QAQCConfirmation, RecordVersion


def _footprint(record: dict):
    bbox = record.get("bounding_box_bbox")
    if not bbox:
        return None
    west, south, east, north = bbox
    if west > east:
        # Antimeridian-crossing boxes need splitting into two polygons;
        # not handled yet, so skip the footprint rather than store a bad shape.
        return None
    polygon = Polygon.from_bbox((west, south, east, north))
    polygon.srid = 4326
    return polygon


@transaction.atomic
def store_record(record: dict, xml: str, user, qaqc_confirmed: bool):
    """Saves record, version 1, provenance, QAQC confirmation and audit entry
    in one transaction: either all rows exist or none do."""
    distribution = record["distribution"]

    obj = MetadataRecord.objects.create(
        status=MetadataRecord.Status.APPROVED,
        current_version=1,
        content=record,
        xml_content=xml,
        footprint=_footprint(record),
        identifier=distribution["identifier"],
        access_url=distribution["access_url"],
        created_by=user,
    )
    version = RecordVersion.objects.create(
        record=obj,
        version_number=1,
        content=record,
        xml_snapshot=xml,
        provenance=record.get("provenance", {}),
        created_by=user,
    )
    if qaqc_confirmed:
        QAQCConfirmation.objects.create(record=obj, version=version, confirmed_by=user)
    QAQCAudit.objects.create(
        record=obj,
        action="SUBMITTED",
        performed_by=user,
        details={"version": 1, "qaqc_confirmed": qaqc_confirmed},
    )
    return obj