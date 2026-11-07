from datetime import datetime
import numpy as np
from osgeo import gdal

gdal.UseExceptions()

def extract_metadata(file_path):

    dataset = gdal.Open(file_path)

    # Metadata
    metadata_creation = datetime.today().date().isoformat()

    # Spatial

    # Identification

    # Author contact info

    # Point of contact

    # Distribution

    #statistics
    band_statistics = extract_band_statistics(dataset)

    extracted = {
        # Metadata
        "identifier": "",
        "language": "",
        "charset": "",
        "hierarchylevel": "",
        "metadata_creation": metadata_creation,

        # Spatial
        "datatype": "",
        "geomtype": "",

        # Identification
        "title": "",
        "abstract": "",
        "identification_language": "",
        "rights": "",
        "url": "",
        "status": "",
        "identification_creation": "",
        "keywords": [],
        "crs": "",
        "bbox": [],

        # Author contact info
        "author_organization": "",
        "author_individualname": "",
        "author_email": "",
        "author_role": "",

        # Point of contact
        "contact_organization": "",
        "contact_individualname": "",
        "contact_email": "",
        "contact_role": "",

        # Distribution
        "format": "",
        "format_version": "",
        "distribution_url": "",
        "distribution_type": "",
        "distribution_name": "",
        "distribution_description": "",
        "distribution_function": "",

        # Raster band statistics
        "band_statistics": band_statistics

    }
    gap_detected = detect_gaps(extracted)
    return gap_detected


def extract_band_statistics(dataset):

    bands = []

    for band_number in range(1, dataset.RasterCount + 1):

        band = dataset.GetRasterBand(band_number)

        nodata = band.GetNoDataValue()

        array = band.ReadAsArray()
        min_val = float(np.min(array))
        max_val = float(np.max(array))
        mean = float(np.mean(array))

        bands.append({
            "band": band_number,
            "min": min_val,
            "max": max_val,
            "mean": mean,
            "nodata": nodata
        })
    
    return bands

def detect_gaps(extracted):

    result = {}

    for key, value in extracted.items():

        if value is None or value == "" or value == []:
            status = "missing"
        else:
            status = "inferred"

        result[key] = {
            "value": value,
            "status": status
        }

    return result



if __name__ == "__main__":
    raster = extract_metadata("file_path")
    print("Raster data:\n")
    print(raster)