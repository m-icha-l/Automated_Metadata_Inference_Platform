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
