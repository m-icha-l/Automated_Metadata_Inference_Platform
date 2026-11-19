"""
Converts our record dict (see serializers.MetadataContentSerializer) into the
pygeometa MCF dict that the engine's xml_generation reads.

Used by services.to_xml(). Keep this file in sync with the record format.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Values our record does not carry. CONFIRM THESE WITH THE TEAM / CUSTOMER.
DEFAULTS = {
    "language": "en",
    "charset": "utf8",
    "hierarchylevel": "dataset",
    "status": "completed",
}


def _iso(value, tz_name):
    """datetime or ISO string -> ISO string in the record's time zone (if it names one)."""
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if tz_name:
        try:
            zone = ZoneInfo(tz_name)
            value = value.replace(tzinfo=zone) if value.tzinfo is None else value.astimezone(zone)
        except ZoneInfoNotFoundError:
            pass  # gap detection requires a time zone; schema validation reports bad ones
    return value.isoformat()


def _keywords(keywords):
    """[{keyword, thesaurus, uri}] -> MCF keyword groups, one group per thesaurus."""
    groups = {}
    for kw in keywords or []:
        thesaurus = (kw.get("thesaurus") or "").strip()
        key = thesaurus.lower().replace(" ", "_") or "default"
        group = groups.setdefault(key, {"keywords": []})
        group["keywords"].append(kw["keyword"])
        if thesaurus:
            group["vocabulary"] = {"name": thesaurus}
    return groups


def record_to_mcf(record: dict) -> dict:
    distribution = record.get("distribution") or {}
    temporal = record.get("temporal_extent") or {}
    tz_name = temporal.get("timezone")

    identification = {
        "title": record.get("title", ""),
        "abstract": record.get("abstract", ""),
        "language": DEFAULTS["language"],
        "status": DEFAULTS["status"],
        "keywords": _keywords(record.get("keywords")),
        "extents": {},
    }
    if record.get("topic_category"):
        identification["topiccategory"] = [record["topic_category"]]

    bbox = record.get("bounding_box_bbox")
    if bbox:
        # Our bbox is always WGS84 lon/lat, so the extent's CRS is 4326 regardless
        # of the dataset's own CRS (record["crs"]).
        identification["extents"]["spatial"] = [{"bbox": list(bbox), "crs": 4326}]
    if temporal.get("start") and temporal.get("end"):
        identification["extents"]["temporal"] = [{
            "begin": _iso(temporal["start"], tz_name),
            "end": _iso(temporal["end"], tz_name),
        }]

    mcf = {
        "mcf": {"version": 2.0},
        "metadata": {
            "language": DEFAULTS["language"],
            "charset": DEFAULTS["charset"],
            "hierarchylevel": DEFAULTS["hierarchylevel"],
            "dates": {"creation": datetime.now(timezone.utc).date().isoformat()},
        },
        "identification": identification,
        "contact": {"pointOfContact": {"email": record.get("contact_email", "")}},
    }

    if record.get("lineage"):
        mcf["dataquality"] = {"scope": {"level": "dataset"},
                              "lineage": {"statement": record["lineage"]}}

    if distribution:
        mcf["metadata"]["identifier"] = distribution["identifier"]
        mcf["distribution"] = {"www": {
            "url": distribution["access_url"],
            "type": "WWW:LINK",
            "name": record.get("title", ""),
            "function": "download",
        }}
    return mcf
