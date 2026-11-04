"""
Task 8: PostgreSQL/PostGIS storage.
 
MetadataRecord     the current state of one dataset's metadata record
RecordVersion      an immutable snapshot of the record at one version number
ProvenanceTag      for one field in one version: was it inferred from the file or typed by a user?
QAQCConfirmation   a user's confirmation of one version on the QAQC screen (who, when, what)
 
Settings: ENGINE "django.contrib.gis.db.backends.postgis" and
"django.contrib.gis" in INSTALLED_APPS.
"""
import uuid
 
from django.conf import settings
from django.contrib.gis.db import models
from django.core.serializers.json import DjangoJSONEncoder
 
 
class MetadataRecord(models.Model):
    """The latest state of a metadata record. Older states live in RecordVersion."""
 
    class Status(models.TextChoices):
        APPROVED = "APPROVED"
        # add e.g. PENDING_REVIEW if records should be reviewed before publishing
 
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.APPROVED, db_index=True)
    current_version = models.PositiveIntegerField(default=1)
 
    # Latest full record as validated JSON (see MetadataContentSerializer)
    content = models.JSONField(encoder=DjangoJSONEncoder)
    xml_content = models.TextField()
 
    # Footprint for spatial queries; derived from content["bounding_box_bbox"]
    footprint = models.PolygonField(srid=4326, null=True, blank=True, spatial_index=True)
 
    # Copied from content["distribution"] so they can be looked up and kept unique
    identifier = models.CharField(max_length=255, unique=True)
    access_url = models.URLField(max_length=1000)
 
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                   on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        ordering = ["-created_at"]
 
    def __str__(self):
        return f"{self.identifier} (v{self.current_version})"
 
 
class RecordVersion(models.Model):
    """One immutable snapshot of a record. A new version never overwrites an old one."""
 
    record = models.ForeignKey(MetadataRecord, on_delete=models.CASCADE,
                               related_name="versions")
    version_number = models.PositiveIntegerField()
    content = models.JSONField(encoder=DjangoJSONEncoder)
    xml_snapshot = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                   on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    provenance = models.JSONField(default=dict)
 
    class Meta:
        ordering = ["record", "-version_number"]
        constraints = [
            models.UniqueConstraint(fields=["record", "version_number"],
                                    name="unique_version_per_record"),
        ]
 
    def __str__(self):
        return f"{self.record.identifier} v{self.version_number}"
 
 
class ProvenanceTag(models.Model):
    """Where one field's value in one version came from."""
 
    class Source(models.TextChoices):
        INFERRED = "inferred"   # worked out from the uploaded file
        USER = "user"           # typed or edited by a person (or an API client)
 
    version = models.ForeignKey(RecordVersion, on_delete=models.CASCADE,
                                related_name="provenance_tags")
    field_name = models.CharField(max_length=100)   # e.g. "title", "bounding_box_bbox"
    source = models.CharField(max_length=10, choices=Source.choices)
    detail = models.CharField(max_length=500, blank=True,
                              help_text="Optional, e.g. which file or method it was inferred from")
    created_at = models.DateTimeField(auto_now_add=True)

    

    class Meta:
        ordering = ["version", "field_name"]
        constraints = [
            models.UniqueConstraint(fields=["version", "field_name"],
                                    name="unique_tag_per_field_and_version"),
        ]
 
    def __str__(self):
        return f"{self.field_name}: {self.source}"
 
 
class QAQCConfirmation(models.Model):
    """A user confirming, on the QAQC screen, that a version's key fields are correct."""
 
    record = models.ForeignKey(MetadataRecord, on_delete=models.CASCADE,
                               related_name="qaqc_confirmations")
    version = models.ForeignKey(RecordVersion, on_delete=models.CASCADE,
                                related_name="qaqc_confirmations")
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                     on_delete=models.SET_NULL, related_name="+")
    confirmed_at = models.DateTimeField(auto_now_add=True)
    # What exactly was confirmed, e.g. {"location": true, "dates": true,
    # "time_zone": true, "value_distribution": true}. Filled in by the QAQC screen (task 4).
    checks = models.JSONField(default=dict, blank=True)
 
    class Meta:
        ordering = ["-confirmed_at"]
 
    def __str__(self):
        return f"{self.record.identifier} v{self.version.version_number} confirmed {self.confirmed_at:%Y-%m-%d %H:%M}"