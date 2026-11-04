# currently supported file formats: .tif .tiff
from pathlib import Path
import json

from raster import read_raster_metadata
# from vector import read_vector_metadata
# from iso_mapping import map_iso_metadata


def identify_file_format(file_path):

    extension = Path(file_path).suffix.lower()

    if extension in [".tif", ".tiff"]:
        return "raster"
    elif extension == [""]:
        return "vector"
    else:
        raise ValueError("Unsupported file format")


def infer_metadata(file_path):

    file_format = identify_file_format(file_path)

    if file_format == "raster":
        metadata = read_raster_metadata(file_path)
    # elif file_format == "vector":
    #     metadata = read_vector_metadata(file_path)

    result = {
        "file_name": Path(file_path).name,
        "format": file_format,
        "inferred_metadata": metadata
    }

    return result


def main():
    file_path = "../samples/LisbonElevation.tif"
    # file_path = "../samples/GeogToWGS84GeoKey5.tif"
    # file_path = "abc"

    metadata = infer_metadata(file_path)
    print(json.dumps(metadata, indent=4))
    # print("\n ####################### \n")
    # iso_mapped = map_iso_metadata(metadata)
    # print(json.dumps(iso_mapped, indent=4))


if __name__ == "__main__":
    main()
