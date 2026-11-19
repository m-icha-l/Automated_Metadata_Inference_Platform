# DIWA Metadata API (tasks 7 and 8)

Django REST API and PostgreSQL/PostGIS storage for the DIWA Upload Portal. A user uploads a
geospatial file, gets a draft ISO 19139 metadata record and a list of missing fields, completes
the record, validates it against the ISO 19139 schema, and submits it. Submitted records are
stored with version history, provenance tags (which values were inferred, which typed by the
user) and a QAQC confirmation.

- **Swagger UI** (try the API in the browser): http://127.0.0.1:8000/api/v1/docs/
- **Django admin** (see what is stored): http://127.0.0.1:8000/admin/
- **OpenAPI schema** (for other systems): http://127.0.0.1:8000/api/v1/schema/

In Swagger, click **Authorize** and log in with the superuser you created.

```
upload file ──> POST /infer/ ──> draft record + gap report
                                   (found values tagged "inferred")
                                         │
                     user completes the record (form)
                                         │
             POST /validate/  or  POST /submit/  ──> services.check_record()
                                                       1. gap detection
                                                       2. record → ISO 19139 XML
                                                       3. XML → XSD schema validation
                                         │
             /submit/ only, if all checks pass:
                assign_identifier()   persistent ID + access URL
                store_record()        record + version + provenance + QAQC, one transaction
                                         │
             GET /records/  and  GET /records/{id}/  ──> read it back
```

`/validate/` and `/submit/` use the same `check_record()`, so an API client cannot skip gap
detection or schema validation. If fields are missing, the XML is not generated, so
`schema_errors` is empty because the schema check was skipped, not because it passed.

## Endpoints

| Method and path | What it does | Responses |
|---|---|---|
| `POST /api/v1/infer/` | Upload a file (multipart field `file`). Returns a draft record and gap report. | 200, 400 (unreadable or unsupported file), 413 (too large) |
| `POST /api/v1/validate/` | Body `{"record": {...}}`. Returns `is_valid`, `gap_report`, `schema_errors`. Always 200, so a form can show the result. | 200 |
| `POST /api/v1/submit/` | Body `{"record": {...}, "qaqc_confirmed": true}`. Same checks, then assigns an identifier and stores the record. | 201 (returns `record_id`), 422 (missing fields or schema errors, nothing stored) |
| (`GET /api/v1/records/` | Stored records, newest first, 50 per page (`?page=`, `?page_size=` up to 200). | 200 )|
| `GET /api/v1/records/{record_id}/` | One record by its UUID (the `record_id` from `/submit/`, not the `diwa:` identifier). | 200, 404 |


## Record format

Defined in `api/serializers.py` --> the contract between the API, the form and the QAQC
screen. Every field is optional in the serializer; completeness is checked by gap detection.

| Field | Notes |
|---|---|
| `title`, `abstract`, `lineage` | text |
| `contact_email` | email |
| `topic_category` | one of the 19 ISO topic categories, e.g. `elevation`, `farming` |
| `keywords` | list of `{keyword, thesaurus (default "GEMET"), uri (optional)}` |
| `crs` | e.g. `EPSG:4326` |
| `bounding_box_bbox` | `[west, south, east, north]` in WGS84 degrees |
| `temporal_extent` | `{start, end, timezone}`; datetimes plus an IANA zone such as `Europe/Helsinki` |
| `statistics` | `{min, max, mean, nodata}` |
| `provenance` | `{field_name: "inferred" or "user"}` |
| `distribution` | `{identifier, access_url}`, set by the server on submit |

The required fields are `REQUIRED_FIELDS` in `api/services.py`: title, abstract, contact_email,
topic_category, keywords, lineage, crs, bounding_box_bbox, temporal_extent.start,
temporal_extent.end, temporal_extent.timezone. The form should ask the API for gaps instead of
keeping its own list.

### Integration with the engine !!

The engine is kept as it is. Everything that connects it to the API is in
`engine_adapters.py`:

- **`infer(path, ext)`** runs `metadata_engine.inference.infer_metadata()` and converts its output
  (`{field: {"value": ..., "status": "inferred" | "missing"}}`) to the API record format. Only
  fields that were actually found are kept; the API then tags them `inferred`.
- **`to_xml(record)`** converts an API record to the engine's flat format (defaults from the
  team's `filled_example.json`), calls `iso_mapping.map_iso_metadata()`, and turns the result
  into ISO 19139 XML with pygeometa.
- **`validate_xml(xml)`** runs `xml_validation.validate_iso19139()` and returns its errors as a
  list of `"line N: message"` strings.

Two engine changes were made: `map_iso_metadata()` in `iso_mapping.py` now takes a dict
that is already in memory (instead of a JSON file) and reads each field with `get_value()`, so a
missing field becomes empty instead of raising `KeyError`; and `xml_generation.py` was split so
`generate_iso19139_from_dict()` can be called with that dict, while `generate_iso19139()` still
reads a JSON file. The engine's imports were adjusted.

`USE_ENGINE_MAPPER = True` in `engine_adapters.py` selects the engine's mapper for XML. Setting
it to `False` uses `mcf.py` instead, which also writes temporal extent, topic category, lineage
and keyword thesauri to the XML.

### GDAL fallback for CRS and bounding box

The engine does not extract the coordinate system or bounding box yet. When they are missing,
`infer()` calls `_georeference()`, which opens the raster with GDAL, reads its coordinate
system and corners, and converts the corners to a WGS84 bounding box. If the file has no
location information, or anything fails, it returns nothing and the fields stay in the gap
report. When the engine extracts these itself, the fallback is simply not used.

Check that it works in your setup:

```bash
docker compose exec web python manage.py shell -c "from api.engine_adapters import _georeference; print(_georeference('LisbonElevation.tif'))"
```
