"""
Task 8: PostgreSQL/PostGIS storage.

MetadataRecord      latest state of a record (+ spatial index on its footprint)
RecordVersion       immutable snapshot per version: content, XML, provenance tags
QAQCConfirmation    who confirmed which version, and when (task 4's "force confirm")
QAQCAudit           general audit trail

Settings: ENGINE "django.contrib.gis.db.backends.postgis" and
"django.contrib.gis" in INSTALLED_APPS.
"""
import uuid

from django.conf import settings
from django.contrib.gis.db import models
from django.core.serializers.json import DjangoJSONEncoder


class MetadataRecord(models.Model):
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


class RecordVersion(models.Model):
    record = models.ForeignKey(MetadataRecord, on_delete=models.CASCADE,
                               related_name="versions")
    version_number = models.PositiveIntegerField()
    content = models.JSONField(encoder=DjangoJSONEncoder)
    xml_snapshot = models.TextField()
    # {"title": "inferred", "abstract": "user", ...} as of this version
    provenance = models.JSONField(default=dict)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                   on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["record", "-version_number"]
        constraints = [
            models.UniqueConstraint(fields=["record", "version_number"],
                                    name="unique_version_per_record"),
        ]


class QAQCConfirmation(models.Model):
    record = models.ForeignKey(MetadataRecord, on_delete=models.CASCADE,
                               related_name="qaqc_confirmations")
    version = models.ForeignKey(RecordVersion, on_delete=models.CASCADE,
                                related_name="qaqc_confirmations")
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                     on_delete=models.SET_NULL, related_name="+")
    confirmed_at = models.DateTimeField(auto_now_add=True)


class QAQCAudit(models.Model):
    record = models.ForeignKey(MetadataRecord, on_delete=models.CASCADE,
                               related_name="audit_log")
    action = models.CharField(max_length=50)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                     on_delete=models.SET_NULL, related_name="+")
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)