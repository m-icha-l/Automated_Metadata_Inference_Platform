"""

Task 8 implementation of the store_record contract from services.py.

In services.py the line `from .storage import store_record` provides it.

"""

from django.contrib.gis.geos import Polygon

from django.db import transaction
 
from .models import (

    MetadataRecord,

    ProvenanceTag,

    QAQCConfirmation,

    RecordVersion,

)
 
 
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
    """Saves record, new version, provenance tags and QAQC confirmation

    in one transaction: either all rows exist or none do."""
    distribution = record["distribution"]
    identifier = distribution["identifier"]

    # Check if a record with this identifier already exists
    existing_record = MetadataRecord.objects.filter(identifier=identifier).first()

    if existing_record:
        # Increment version for the existing record
        new_version_number = existing_record.current_version + 1
        
        # Update the main record fields
        existing_record.status = MetadataRecord.Status.APPROVED
        existing_record.current_version = new_version_number
        existing_record.content = record
        existing_record.xml_content = xml
        existing_record.footprint = _footprint(record)
        existing_record.access_url = distribution["access_url"]
        existing_record.save()
        
        obj = existing_record
    else:
        # Create brand new record at version 1
        new_version_number = 1
        obj = MetadataRecord.objects.create(
            status=MetadataRecord.Status.APPROVED,
            current_version=1,
            content=record,
            xml_content=xml,
            footprint=_footprint(record),
            identifier=identifier,
            access_url=distribution["access_url"],
            created_by=user,
        )

    # Create the immutable snapshot version
    version = RecordVersion.objects.create(
        record=obj,
        version_number=new_version_number,
        content=record,
        xml_snapshot=xml,
        created_by=user,
        provenance=record.get("provenance", {}),
    )

    ProvenanceTag.objects.bulk_create([
        ProvenanceTag(version=version, field_name=field, source=source)
        for field, source in (record.get("provenance") or {}).items()
    ])

    if qaqc_confirmed:
        QAQCConfirmation.objects.create(record=obj, version=version, confirmed_by=user)

    return obj

@transaction.atomic
def update_record(record_id, record: dict, xml: str, user, qaqc_confirmed: bool):
    """Updates an existing record, increments version, and saves a new snapshot."""
    
    # 1. Fetch the existing record
    obj = MetadataRecord.objects.get(id=record_id)
    
    # 2. Increment version and update main fields
    obj.current_version += 1
    obj.content = record
    obj.xml_content = xml
    obj.footprint = _footprint(record)
    obj.save()
    
    # 3. Create the new immutable version snapshot
    version = RecordVersion.objects.create(
        record=obj,
        version_number=obj.current_version,
        content=record,
        xml_snapshot=xml,
        created_by=user,
    )
    
    # 4. Map provenance tags for this new version
    ProvenanceTag.objects.bulk_create([
        ProvenanceTag(version=version, field_name=field, source=source)
        for field, source in (record.get("provenance") or {}).items()
    ])
    
    # 5. Log QAQC confirmation if checked
    if qaqc_confirmed:
        QAQCConfirmation.objects.create(record=obj, version=version, confirmed_by=user)
        
    return obj