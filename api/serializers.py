"""
Serializers = the contract between the API, the upload form (task 3),
the QAQC screen (task 4) and the pipeline (tasks 1, 5, 6, 8).
drf-spectacular generates the OpenAPI schema from these.
"""
from rest_framework import serializers

# ISO 19115/19139 MD_TopicCategoryCode
ISO_TOPIC_CATEGORIES = [
    "farming", "biota", "boundaries", "climatologyMeteorologyAtmosphere",
    "economy", "elevation", "environment", "geoscientificInformation",
    "health", "imageryBaseMapsEarthCover", "intelligenceMilitary",
    "inlandWaters", "location", "oceans", "planningCadastre", "society",
    "structure", "transportation", "utilitiesCommunication",
]
PROVENANCE_CHOICES = ["inferred", "user"]


class KeywordSerializer(serializers.Serializer):
    keyword = serializers.CharField()
    thesaurus = serializers.CharField(default="GEMET")
    uri = serializers.URLField(required=False, allow_blank=True)


class TemporalExtentSerializer(serializers.Serializer):
    start = serializers.DateTimeField(required=False, allow_null=True)
    end = serializers.DateTimeField(required=False, allow_null=True)
    timezone = serializers.CharField(
        required=False, allow_blank=True, help_text="IANA zone, e.g. Europe/Helsinki"
    )

    def validate(self, attrs):
        start, end = attrs.get("start"), attrs.get("end")
        if start and end and end < start:
            raise serializers.ValidationError("end must not be before start")
        return attrs


class StatisticsSerializer(serializers.Serializer):
    min = serializers.FloatField(required=False, allow_null=True)
    max = serializers.FloatField(required=False, allow_null=True)
    mean = serializers.FloatField(required=False, allow_null=True)
    nodata = serializers.FloatField(required=False, allow_null=True)


class DistributionSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    access_url = serializers.URLField()


    def validate_bounding_box_bbox(self, value):
        if value is None:
            return value
        west, south, east, north = value
        if not (-180 <= west <= 180 and -180 <= east <= 180
                and -90 <= south <= 90 and -90 <= north <= 90):
            raise serializers.ValidationError("bbox must be WGS84 lon/lat")
        if south > north:
            raise serializers.ValidationError("south must not exceed north")
        return value


class MetadataContentSerializer(serializers.Serializer):
    """The metadata record itself. Every field is optional here: completeness
    is enforced by gap detection (services.find_gaps), not by the serializer,
    so drafts can be round-tripped through the form."""

    title = serializers.CharField(required=False, allow_blank=True)
    abstract = serializers.CharField(required=False, allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    topic_category = serializers.ChoiceField(
        choices=ISO_TOPIC_CATEGORIES, required=False, allow_blank=True
    )
    keywords = KeywordSerializer(many=True, required=False)
    lineage = serializers.CharField(required=False, allow_blank=True)
    crs = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    bounding_box_bbox = serializers.ListField(
        child=serializers.FloatField(), min_length=4, max_length=4,
        required=False, allow_null=True,
        help_text="[west, south, east, north] in WGS84 lon/lat",
    )
    temporal_extent = TemporalExtentSerializer(required=False)
    statistics = StatisticsSerializer(required=False)
    distribution = DistributionSerializer(
        read_only=True, help_text="Assigned by the server on submission"
    )
    provenance = serializers.DictField(
        child=serializers.ChoiceField(choices=PROVENANCE_CHOICES),
        required=False,
        help_text="Per-field origin: 'inferred' or 'user'",
    )

    def validate_bounding_box_bbox(self, value):
        if value is None:
            return value
        west, south, east, north = value
        if not (-180 <= west <= 180 and -180 <= east <= 180
                and -90 <= south <= 90 and -90 <= north <= 90):
            raise serializers.ValidationError("bbox must be WGS84 lon/lat")
        if south > north:
            raise serializers.ValidationError("south must not exceed north")
        return value

class GapReportSerializer(serializers.Serializer):
    missing_fields = serializers.ListField(
        child=serializers.CharField(), help_text="Dotted paths, e.g. temporal_extent.start"
    )
    is_complete = serializers.BooleanField()


# infer 
class InferInputSerializer(serializers.Serializer):
    file = serializers.FileField()


class InferResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    draft_record = MetadataContentSerializer()
    gap_report = GapReportSerializer()


# validate 
class ValidateInputSerializer(serializers.Serializer):
    record = MetadataContentSerializer()


class ValidateResponseSerializer(serializers.Serializer):
    is_valid = serializers.BooleanField()
    gap_report = GapReportSerializer()
    schema_errors = serializers.ListField(child=serializers.CharField())


# submit 
class SubmitInputSerializer(serializers.Serializer):
    record = MetadataContentSerializer()
    # OPEN QUESTION (task 4): must API submissions carry a QAQC confirmation?
    # Stored with the record history but not enforced yet.
    qaqc_confirmed = serializers.BooleanField(default=False)


class SubmitResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    record_id = serializers.UUIDField()
    version = serializers.IntegerField()
    identifier = serializers.CharField()
    access_url = serializers.URLField()


# retrieval
class RecordSerializer(serializers.Serializer):
    # Assumes task 8 models: MetadataRecord(id, status, current_version,
    # content JSON, created_at, updated_at). Adjust `source` once they exist.
    id = serializers.UUIDField(read_only=True)
    status = serializers.CharField(read_only=True)
    current_version = serializers.IntegerField(read_only=True)
    record = MetadataContentSerializer(source="content", read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class ErrorSerializer(serializers.Serializer):
    error = serializers.CharField()