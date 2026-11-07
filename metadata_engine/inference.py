from pathlib import Path
import json

from metadata_extraction import extract_metadata

def infer_metadata(file_path):

    extension = Path(file_path).suffix.lower()

    if extension in [".tif", ".tiff"]:
        metadata = extract_metadata(file_path)
    else:
        raise ValueError("Unsupported file format")

    return metadata


def main():

    # file_path = "../samples/LisbonElevation.tif"
    file_path = "../samples/GeogToWGS84GeoKey5.tif"
    # file_path = "abc"

    metadata = infer_metadata(file_path)
    output_path = Path("../metadata_engine/json/") / Path(file_path).with_suffix(".json").name

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
