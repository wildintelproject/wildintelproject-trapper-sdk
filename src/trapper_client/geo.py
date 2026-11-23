"""Small geographic helpers used to filter locations on the client."""
from __future__ import annotations

import math

#: Mean radius of the Earth, in metres (the sphere the haversine formula assumes).
EARTH_RADIUS_M = 6_371_008.8


def distance_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance in metres between two ``(longitude, latitude)`` points (haversine)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def in_bbox(lon: float, lat: float, bbox: tuple[float, float, float, float]) -> bool:
    """Whether a point is inside ``(min_lon, min_lat, max_lon, max_lat)``, edges included.

    A box with ``min_lon > max_lon`` is read as crossing the antimeridian (±180°).
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    if not min_lat <= lat <= max_lat:
        return False
    if min_lon <= max_lon:
        return min_lon <= lon <= max_lon
    return lon >= min_lon or lon <= max_lon
