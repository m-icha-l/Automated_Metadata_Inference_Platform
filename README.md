# DIWA Metadata Inference Platform

A separate service that reads files being uploaded to the DIWA Upload Portal, guesses their metadata (ISO 19115/19139), asks the user to fill the gaps, and requires a visual check before the upload continues.

**Deadline:** 11 Dec 2026

## How it works

1. The portal's upload button sends the user to this service.
2. The service reads the file and pre-fills a metadata form.
3. The user fixes wrong guesses and fills required fields.
4. A popup shows location, dates and a value chart for confirmation.
5. The record is saved as ISO 19139 and the user returns to the portal to finish the upload.

## Links

- DIWA Upload Portal: https://fip-86-50-231-86.kaj.poutavm.fi/
- GitHub: DigitalWaters-fi
- GDAL: https://gdal.org/en/stable/
- exif: https://exif.readthedocs.io/en/latest/usage.html

**Status:** working skeleton. Gap detection, the validation gate, storage, versioning and the
OpenAPI docs are implemented. Inference, XML serialisation, schema validation and identifier
assignment are stubs owned by other tasks (see [Who owns what](#who-owns-what)). Until they
are replaced, `/infer/` and any submission that passes gap detection return **501**.

## How it fits together

```
upload -> /infer/ -> draft record + gap report
                        |
 form/QAQC screen edits the record (tasks 3, 4)
                        |
         /validate/ or /submit/  ->  services.check_record():
                                       1. find_gaps(record)
                                       2. to_xml(record)        (pygeometa, task 5)
                                       3. validate_xml(xml)     (XSD, task 5)
                        |
 /submit/ only, if the checks pass:
     assign_identifier(record)     (task 6)  -> distribution info
     check_record again (the XML now includes the identifier)
     store_record(...)             (task 8)  -> one transaction
```

`/validate/` and `/submit/` call the same `check_record()`, so API clients cannot bypass gap
detection or schema validation. Views contain no business logic; they call functions in
`api/services.py`.

## Setup

### Quick start with Docker

Needs only Docker Desktop (or Docker Engine with the Compose plugin). No need to install
Python, GDAL, GEOS or PostGIS on your computer.

1. Create your environment file and choose a database password:

   ```bash
   cp .env.example .env
   ```

   Open `.env` and set `DB_PASSWORD=...`. Never commit `.env`.

2. Start the database and the API:

   ```bash
   docker compose up --build
   ```

   The first build takes a few minutes. When the log says
   `Starting development server at http://0.0.0.0:8000/`, the API is running. On start,
   the `web` service applies the database migrations automatically.

3. In a second terminal, in the same folder, create a login:

   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

4. Open the API:

   - Swagger UI (API documentation): http://127.0.0.1:8000/api/v1/docs/
   - Admin (read-only view of the stored data): http://127.0.0.1:8000/admin/

   Log in at `/admin/` first. All endpoints require authentication.

#### commands

| Task | Command |
|---|---|
| Start in the background | `docker compose up -d` |
| Stop | `docker compose down` |
| Follow the logs | `docker compose logs -f web` |
| Run the tests | `docker compose exec web python manage.py test api` |
| Create migrations after changing `models.py` | `docker compose exec web python manage.py makemigrations api` |
| Apply migrations | `docker compose exec web python manage.py migrate` |
| Export the OpenAPI file | `docker compose exec web python manage.py spectacular --validate --file openapi.yaml` |
| Open a Django shell | `docker compose exec web python manage.py shell` |
| Reset the database (deletes all data) | `docker compose down -v` |

Code changes on your computer appear in the running container straight away, because the
project folder is mounted into it. After changing `requirements.txt` or the `Dockerfile`,
run `docker compose up --build` again.

#### Trouble?

- **`password authentication failed`:** the database keeps the password it was created with.
  Put the original password back in `.env`, or reset with `docker compose down -v`.
- **`service "web" is not running`:** the container stopped. Run `docker compose logs web`
  to see why.
- **`port is already allocated`:** another program uses port 5432 or 8000. Stop it, or
  change the port mapping in `docker-compose.yml`.
- **`DB_PASSWORD` error on start:** `.env` is missing, or it is not in the same folder as
  `docker-compose.yml`.

### Option B: run Django on your own machine

Use this if you prefer your own Python environment. The database still runs in Docker.

1. Start only the database:

   ```bash
   cp .env.example .env          # set DB_PASSWORD
   docker compose up -d db
   ```

2. Install GDAL, GEOS and PROJ.
   - Ubuntu/Debian: `sudo apt install gdal-bin libgdal-dev libgeos-dev libproj-dev`
   - macOS: `brew install gdal geos proj` compiles for a long time; conda-forge is lighter:
     `brew install micromamba && micromamba create -n geo -c conda-forge gdal geos proj`

3. Create a Python environment and install the packages:

   ```bash
   python3 -m venv env && source env/bin/activate
   python3 -m pip install -r requirements.txt
   ```

4. Set the environment variables in every new terminal:

   ```bash
   export DB_PASSWORD=...        # same as in .env
   export GDAL_LIBRARY_PATH=/path/to/libgdal.dylib   # only if Django can't find GDAL
   export GEOS_LIBRARY_PATH=/path/to/libgeos_c.dylib # only if Django can't find GEOS
   ```

5. Run:

   ```bash
   python3 manage.py migrate
   python3 manage.py createsuperuser
   python3 manage.py runserver
   ```

- API docs (Swagger UI): http://127.0.0.1:8000/api/v1/docs/
- OpenAPI file: `python3 manage.py spectacular --validate --file openapi.yaml`

### 6. Tests

```bash
python3 manage.py test api
```

The tests replace the other tasks' functions with fakes, so they run without those tasks.
Django creates and deletes a temporary `test_diwa` database.

## Endpoints

All endpoints require authentication (session login, or HTTP basic auth for scripts).

| Method and path | Purpose | Responses |
|---|---|---|
| `POST /api/v1/infer/` | Upload a file (multipart `file`), get a draft record and gap report. Fields it fills are tagged `inferred`. | 200, 400 (bad or unsupported file), 413, 501 |
| `POST /api/v1/validate/` | Body `{"record": {...}}`. Returns `is_valid`, `gap_report`, `schema_errors`. Always 200 so forms can render the result. | 200, 501 |
| `POST /api/v1/submit/` | Body `{"record": {...}, "qaqc_confirmed": bool}`. Runs the same checks, assigns an identifier, stores the record. | 201, 422 (gaps or schema errors; nothing stored), 501 |
| `GET /api/v1/records/` | Approved records, paginated (50 per page, `?page=`, `?page_size=`). | 200 |
| `GET /api/v1/records/<uuid>/` | One approved record. | 200, 404 |

## Record format

Defined in `api/serializers.py` (`MetadataContentSerializer`); this is the contract between the
API, the form, the QAQC screen and the pipeline. Every field is optional in the serializer;
completeness is enforced by gap detection.

| Field | Notes |
|---|---|
| `title`, `abstract`, `lineage` | text |
| `contact_email` | email |
| `topic_category` | one of the 19 ISO `MD_TopicCategoryCode` values |
| `keywords` | list of `{keyword, thesaurus (default "GEMET"), uri}` |
| `crs` | e.g. `EPSG:3067` |
| `bounding_box_bbox` | `[west, south, east, north]`, WGS84 lon/lat |
| `temporal_extent` | `{start, end, timezone}`, datetimes with an IANA time zone |
| `statistics` | `{min, max, mean, nodata}` |
| `provenance` | `{field: "inferred" \| "user"}` |
| `distribution` | `{identifier, access_url}`, read-only, set by the server on submit |

Fields required by gap detection are listed in `REQUIRED_FIELDS` in `api/services.py`
(dotted paths, e.g. `temporal_extent.start`). The form should ask the API for gaps rather than
keep its own list.

## Storage (task 8, PostgreSQL/PostGIS)

PostGIS tables in `api/models.py`:

- `MetadataRecord`: the current state of one dataset's metadata record
- `RecordVersion`: an immutable snapshot of the record at one version number
- `ProvenanceTag`: for one field in one version: was it inferred from the file or typed by a user?
- `QAQCConfirmation`: a user's confirmation of one version on the QAQC screen (who, when, what)

`store_record()` (`api/storage.py`) writes all of these in one transaction.

## Who owns what

Each stub lives in `api/services.py` and raises `NotYetImplemented` (HTTP 501) until replaced.
Keep the signature; the docstring in the file is the full contract.

| Task | Function | Returns |
|---|---|---|
| 1 Inference | `infer(path, ext)` | draft record dict; raise `UnreadableFile` for corrupt input. Also owns `SUPPORTED_EXTENSIONS`. |
| 5 Schema validation | `to_xml(record)` | ISO 19139 XML string (pygeometa) |
| 5 Schema validation | `validate_xml(xml)` | list of error strings, empty if valid. Use a hardened XML parser. |
| (6 Identifier and URL | `assign_identifier(record)` | `{"identifier": ..., "access_url": ...}`) |
| 3 Form, 4 QAQC screen | none | build against `openapi.yaml`; call the API |
| 7 API, 8 Storage | everything else | done in this repository |

To change the record format, edit `serializers.py` --> tell the group because everyone builds on it.

## API documentation (OpenAPI and Swagger UI)

The API is documented with OpenAPI. The description is generated automatically from the serializers and views by
`drf-spectacular`, so it always matches the code.

- **OpenAPI file:** `GET /api/v1/schema/` returns the description of every endpoint: the
  URLs, the fields each one accepts and returns, and the possible responses (200, 400,
  422, 501,...). To save it as a file, run:
  `python3 manage.py spectacular --validate --file openapi.yaml`.
  Other teams can read this file, or generate client code from it, without running the server.

- **Swagger UI:** `http://127.0.0.1:8000/api/v1/docs/` shows the same description as an
  interactive web page. Each endpoint can be expanded to see its fields and example
  responses. Click **Try it out** and **Execute** to send a real request to the running
  server and see the response. Log in at `/admin/` first, or use the **Authorize** button,
  because all endpoints require authentication.

Swagger UI only works while the server is running. The committed `openapi.yaml` is the
version of the documentation to share with the group.

## Open questions

1. Must API submissions include a QAQC confirmation? `qaqc_confirmed` is stored but not enforced.
2. Should approved records be readable without logging in? Currently login is required.
3. Does a successful submit become `APPROVED` immediately, or is there a review step first?
