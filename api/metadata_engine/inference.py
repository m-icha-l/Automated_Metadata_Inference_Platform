import json
from pathlib import Path

#fixes ModuleNotFoundError
try:
    from .metadata_extraction import extract_metadata   # inside Django
except ImportError:
    from metadata_extraction import extract_metadata    # running the script directly

SUPPORTED_FILE_EXTENSIONS = [".shp", ".geojson", ".json", ".kml", ".txt", ".xls", ".xlsx",
                              ".tif", ".tiff", ".asc",
                              ".hdf", ".hdf5", ".nc"]

def infer_metadata(file_path):

    extension = Path(file_path).suffix.lower()

    if extension in SUPPORTED_FILE_EXTENSIONS:
        metadata = extract_metadata(file_path)
    else:
        raise ValueError("Unsupported file format")

    return metadata


if __name__ == "__main__":
    file_path = "../samples/LisbonElevation.tif"
    # file_path = "../samples/GeogToWGS84GeoKey5.tif"
    # file_path = "abc"

    metadata = infer_metadata(file_path)

    output_dir = Path(__file__).resolve().parent / "generated_json"
    output_file = output_dir / (Path(file_path).stem + ".json")

    output_file.write_text(
        json.dumps(metadata, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )