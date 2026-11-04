from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from api import services
from api.models import MetadataRecord, QAQCAudit, QAQCConfirmation, RecordVersion

User = get_user_model()

VALID_RECORD = {
    "title": "Test lake survey",
    "abstract": "Depth measurements.",
    "contact_email": "a@example.com",
    "topic_category": "inlandWaters",
    "keywords": [{"keyword": "lakes", "thesaurus": "GEMET"}],
    "lineage": "Measured in 2025.",
    "crs": "EPSG:4326",
    "bounding_box_bbox": [24.0, 64.0, 26.0, 66.0],
    "temporal_extent": {
        "start": "2025-06-01T00:00:00Z",
        "end": "2025-06-30T00:00:00Z",
        "timezone": "Europe/Helsinki",
    },
    "statistics": {"min": 0.5, "max": 12.0, "mean": 4.2, "nodata": -9999},
}


class ApiTestBase(TestCase):
    """Replaces the other tasks' functions with fakes."""

    def setUp(self):
        self.user = User.objects.create_user("tester", password="pw")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

        patches = {
            "to_xml": patch("api.services.to_xml", return_value="<xml/>"),
            "validate_xml": patch("api.services.validate_xml", return_value=[]),
            "assign_identifier": patch(
                "api.services.assign_identifier",
                return_value={"identifier": "diwa:test-1",
                              "access_url": "https://example.org/data/1"},
            ),
        }
        for name, p in patches.items():
            setattr(self, name, p.start())
            self.addCleanup(p.stop)

    def submit(self, record, **extra):
        return self.client.post(
            "/api/v1/submit/", {"record": record, **extra}, format="json"
        )

    def assertNothingStored(self):
        self.assertEqual(MetadataRecord.objects.count(), 0)
        self.assertEqual(RecordVersion.objects.count(), 0)
        self.assertEqual(QAQCConfirmation.objects.count(), 0)
        self.assertEqual(QAQCAudit.objects.count(), 0)


class GapDetectionTests(TestCase):
    def test_empty_record_has_all_gaps(self):
        self.assertEqual(services.find_gaps({}), services.REQUIRED_FIELDS)

    def test_complete_record_has_no_gaps(self):
        self.assertEqual(services.find_gaps(VALID_RECORD), [])


class AuthTests(TestCase):
    def test_unauthenticated_requests_are_rejected(self):
        client = APIClient()
        for url in ("/api/v1/validate/", "/api/v1/submit/"):
            response = client.post(url, {"record": {}}, format="json")
            self.assertIn(response.status_code, (401, 403))
        self.assertIn(client.get("/api/v1/records/").status_code, (401, 403))


class InferTests(ApiTestBase):
    def test_inferred_fields_are_tagged_and_gaps_reported(self):
        draft = {"crs": "EPSG:4326", "bounding_box_bbox": [24.0, 64.0, 26.0, 66.0]}
        with patch("api.services.infer", return_value=draft):
            upload = SimpleUploadedFile("data.tif", b"not really a tiff")
            response = self.client.post("/api/v1/infer/", {"file": upload},
                                        format="multipart")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["draft_record"]["provenance"],
                         {"crs": "inferred", "bounding_box_bbox": "inferred"})
        self.assertIn("title", response.data["gap_report"]["missing_fields"])
        self.assertFalse(response.data["gap_report"]["is_complete"])

    def test_unsupported_file_type_rejected(self):
        upload = SimpleUploadedFile("notes.exe", b"x")
        response = self.client.post("/api/v1/infer/", {"file": upload},
                                    format="multipart")
        self.assertEqual(response.status_code, 400)


class ValidateTests(ApiTestBase):
    def test_incomplete_record_reports_gaps(self):
        response = self.client.post("/api/v1/validate/", {"record": {}}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_valid"])
        self.assertIn("title", response.data["gap_report"]["missing_fields"])

    def test_complete_record_is_valid(self):
        response = self.client.post("/api/v1/validate/", {"record": VALID_RECORD},
                                    format="json")
        self.assertTrue(response.data["is_valid"])


class SubmitGateTests(ApiTestBase):
    """Submission must not bypass gap detection or schema validation."""

    def test_incomplete_record_is_rejected_and_nothing_stored(self):
        record = {k: v for k, v in VALID_RECORD.items() if k != "title"}
        response = self.submit(record)
        self.assertEqual(response.status_code, 422)
        self.assertIn("title", response.data["gap_report"]["missing_fields"])
        self.assertNothingStored()
        self.assign_identifier.assert_not_called()

    def test_schema_errors_are_rejected_and_nothing_stored(self):
        self.validate_xml.return_value = ["element 'x' is not allowed"]
        response = self.submit(VALID_RECORD)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["schema_errors"], ["element 'x' is not allowed"])
        self.assertNothingStored()
        self.assign_identifier.assert_not_called()

    def test_validate_and_submit_report_the_same_gaps(self):
        validate = self.client.post("/api/v1/validate/", {"record": {}}, format="json")
        submit = self.submit({})
        self.assertEqual(validate.data["gap_report"], submit.data["gap_report"])


class SubmitStorageTests(ApiTestBase):
    def test_valid_record_is_stored_with_version_provenance_and_audit(self):
        response = self.submit(VALID_RECORD, qaqc_confirmed=True)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["identifier"], "diwa:test-1")

        record = MetadataRecord.objects.get()
        self.assertEqual(record.identifier, "diwa:test-1")
        self.assertIsNotNone(record.footprint)
        self.assertEqual(record.created_by, self.user)

        version = RecordVersion.objects.get()
        self.assertEqual(version.version_number, 1)
        self.assertEqual(version.provenance["title"], "user")

        confirmation = QAQCConfirmation.objects.get()
        self.assertEqual(confirmation.confirmed_by, self.user)
        self.assertIsNotNone(confirmation.confirmed_at)
        self.assertEqual(QAQCAudit.objects.count(), 1)

    def test_no_confirmation_row_when_not_confirmed(self):
        self.submit(VALID_RECORD)
        self.assertEqual(QAQCConfirmation.objects.count(), 0)

    def test_failed_write_leaves_no_partial_rows(self):
        with patch("api.storage.QAQCAudit.objects.create",
                   side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                self.submit(VALID_RECORD, qaqc_confirmed=True)
        self.assertNothingStored()


class RetrievalTests(ApiTestBase):
    def test_list_and_detail(self):
        self.submit(VALID_RECORD)
        listing = self.client.get("/api/v1/records/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["count"], 1)

        record_id = MetadataRecord.objects.get().id
        detail = self.client.get(f"/api/v1/records/{record_id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["record"]["title"], "Test lake survey")