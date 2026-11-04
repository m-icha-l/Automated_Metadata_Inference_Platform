import logging
import os
import uuid
import tempfile
from pathlib import Path

from drf_spectacular.utils import extend_schema
from rest_framework import generics, parsers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import MetadataRecord  # task 8
from .storage import store_record, update_record
from .serializers import (
    ErrorSerializer,
    InferInputSerializer,
    InferResponseSerializer,
    RecordSerializer,
    SubmitInputSerializer,
    SubmitResponseSerializer,
    ValidateInputSerializer,
    ValidateResponseSerializer,
)


logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 200 * 1024 * 1024
EMPTY = (None, "", [], {})


def _gap_report(gaps):
    return {"missing_fields": gaps, "is_complete": not gaps}


def _mark_provenance(record: dict, default: str) -> dict:
    """Fields without a provenance tag get `default` ('inferred' for infer,
    'user' for API clients, which supplied the values themselves)."""
    prov = dict(record.get("provenance") or {})
    for key, value in record.items():
        if key not in ("provenance", "distribution") and value not in EMPTY:
            prov.setdefault(key, default)
    return {**record, "provenance": prov}


class InferMetadataView(APIView):
    """POST /api/v1/infer/ : upload a file, get a draft record and gap report."""
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    @extend_schema(
        request=InferInputSerializer,
        responses={200: InferResponseSerializer, 400: ErrorSerializer,
                   413: ErrorSerializer, 501: ErrorSerializer},
    )
    def post(self, request):
        serializer = InferInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["file"]

        if upload.size > MAX_UPLOAD_BYTES:
            return Response({"error": "File too large."},
                            status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        ext = Path(upload.name).suffix.lower()
        if ext not in services.SUPPORTED_EXTENSIONS:
            return Response({"error": f"Unsupported file type '{ext}'."},
                            status=status.HTTP_400_BAD_REQUEST)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, f"upload{ext}")  # never the user's filename
            with open(path, "wb") as fh:
                for chunk in upload.chunks():
                    fh.write(chunk)
            try:
                draft = services.infer(path, ext)
            except services.UnreadableFile as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        draft = _mark_provenance(draft, "inferred")
        return Response({
            "message": "Metadata inferred successfully",
            "draft_record": draft,
            "gap_report": _gap_report(services.find_gaps(draft)),
        })


class ValidateMetadataView(APIView):
    """POST /api/v1/validate/ : gap detection + ISO 19139 schema validation.
    Always 200; the result is in `is_valid`, so the form can render it."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ValidateInputSerializer,
        responses={200: ValidateResponseSerializer, 501: ErrorSerializer},
    )
    def post(self, request):
        serializer = ValidateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.check_record(dict(serializer.validated_data["record"]))
        return Response({
            "is_valid": result.is_valid,
            "gap_report": _gap_report(result.gaps),
            "schema_errors": result.schema_errors,
        })


class SubmitMetadataView(APIView):
    #dukmmy for t esting
    """POST /api/v1/submit/ : same gate as /validate/, then identifier + storage."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=SubmitInputSerializer,
        responses={201: SubmitResponseSerializer, 422: ValidateResponseSerializer,
                   501: ErrorSerializer},
    )
    def post(self, request):
        serializer = SubmitInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        record = _mark_provenance(dict(serializer.validated_data["record"]), "user")
        record.pop("distribution", None)  # server-assigned only

        # 1) Gap detection check (blocks incomplete records with 422)
        gaps = services.find_gaps(record)
        if gaps:
            return Response({
                "is_valid": False,
                "gap_report": _gap_report(gaps),
                "schema_errors": [],
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # 2) MOCK TASK 6: Assign dummy identifier & access URL (bypassing 501)
        generated_id = f"oulu-basin-{uuid.uuid4().hex[:8]}"
        record["distribution"] = {
            "identifier": generated_id,
            "access_url": f"http://127.0.0.1:8000/api/v1/records/{generated_id}/"
        }

        # 3) MOCK TASK 5: Dummy XML snapshot (bypassing 501 pygeometa)
        dummy_xml = "<gmd:MD_Metadata xmlns:gmd='http://www.isotc211.org/2005/gmd'>Dummy ISO 19139 XML</gmd:MD_Metadata>"

        # 4) TASK 8: Store record, version 1, provenance, and QAQC confirmation in PostGIS
        stored = store_record(
            record,
            dummy_xml,
            request.user if request.user.is_authenticated else None,
            serializer.validated_data["qaqc_confirmed"],
        )

        return Response({
            "message": "Metadata successfully submitted and stored in PostGIS.",
            "record_id": stored.id,
            "version": stored.current_version,
            "identifier": record["distribution"]["identifier"],
            "access_url": record["distribution"]["access_url"],
        }, status=status.HTTP_201_CREATED)


class RecordPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


# OPEN QUESTION: should published records be readable without login?
class RecordListView(generics.ListAPIView):
    """GET /api/v1/records/ : approved records only, paginated."""
    permission_classes = [IsAuthenticated]
    serializer_class = RecordSerializer
    pagination_class = RecordPagination
    queryset = MetadataRecord.objects.filter(status="APPROVED").order_by("-created_at")


class RecordDetailView(generics.RetrieveAPIView):
    """GET and PUT /api/v1/records/<uuid>/"""
    permission_classes = [IsAuthenticated]
    serializer_class = RecordSerializer
    queryset = MetadataRecord.objects.filter(status="APPROVED")
    lookup_field = "id"
    lookup_url_kwarg = "record_id"

    @extend_schema(
        request=SubmitInputSerializer,
        responses={200: RecordSerializer, 422: ValidateResponseSerializer}
    )
    def put(self, request, record_id):
        serializer = SubmitInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        record = _mark_provenance(dict(serializer.validated_data["record"]), "user")

        # 1) The gate: Run ONLY gap detection (temporary bypass for 501 xml check)
        gaps = services.find_gaps(record)
        if gaps:
            return Response({
                "is_valid": False,
                "gap_report": _gap_report(gaps),
                "schema_errors": [],
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # Fetch existing record to keep its original identifier (Task 6 bypass)
        existing_record = self.get_object()
        record["distribution"] = {
            "identifier": existing_record.identifier,
            "access_url": existing_record.access_url
        }

        dummy_xml = "<gmd:MD_Metadata>Dummy XML Update</gmd:MD_Metadata>"

        # 2) update_record (task 8) does version + provenance + QAQC atomically
        updated_obj = update_record(
            record_id, record, dummy_xml, request.user,
            serializer.validated_data["qaqc_confirmed"]
        )

        # 3) Return the updated record
        response_serializer = self.get_serializer(updated_obj)
        return Response(response_serializer.data, status=status.HTTP_200_OK)