import pytest

from neighborhood_fit.commute import build_request, parse_response

N = [
    {"neighborhood_id": "a", "lat": "32.7", "lon": "-117.1"},
    {"neighborhood_id": "b", "lat": "32.8", "lon": "-117.2"},
]
H = [{"hub_id": "x", "lat": "32.9", "lon": "-117.3"}]


def test_build_request_orders_lon_lat_and_indexes():
    req = build_request(N, H)
    assert req["locations"][0] == [-117.1, 32.7]
    assert req["sources"] == [0, 1]
    assert req["destinations"] == [2]


def test_parse_response_converts_seconds_to_minutes():
    rows = parse_response({"durations": [[600.0], [1830.0]]}, N, H)
    assert rows == [
        {"neighborhood_id": "a", "hub_id": "x", "minutes": 10.0},
        {"neighborhood_id": "b", "hub_id": "x", "minutes": 30.5},
    ]


def test_parse_response_rejects_missing_route():
    with pytest.raises(ValueError):
        parse_response({"durations": [[None], [60.0]]}, N, H)


def test_build_osrm_url_one_request_lon_lat_order():
    from neighborhood_fit.commute import build_osrm_url
    url = build_osrm_url(N, H)
    assert url.startswith("https://router.project-osrm.org/table/v1/driving/-117.1,32.7;-117.2,32.8;-117.3,32.9?")
    assert "sources=0;1" in url and "destinations=2" in url
