from osgeo import gdal

def read_raster_metadata(file_path):

    dataset = gdal.Open(file_path)

    extracted = {

        "metadata": dataset.GetMetadata(),
        "metadata_domains": dataset.GetMetadataDomainList(),
        "geotransform": dataset.GetGeoTransform(),
        "projection": dataset.GetProjection(),
        "driver": dataset.GetDriver().ShortName,
        "gcps": dataset.GetGCPs(),
        "gcp_projection": dataset.GetGCPProjection(),
        "bands": []

    }

    return extracted
