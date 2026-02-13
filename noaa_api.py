from collections import defaultdict
from math import radians, sin, cos, sqrt, atan2
import requests
import streamlit as st

NOAA_HEADERS = {"User-Agent": "streamlit-weather-app"}


# -------------------------------------------------------------------
# Fetch nearby NOAA stations
# -------------------------------------------------------------------
def get_ghcnd_stations(lat, lon, radius_deg=0.5):
    """
    Return GHCND stations near a lat/lon using NCEI.
    radius_deg ~ 0.5 degrees ≈ 35 miles
    """
    min_lat = lat - radius_deg
    max_lat = lat + radius_deg
    min_lon = lon - radius_deg
    max_lon = lon + radius_deg

    url = (
        "https://www.ncei.noaa.gov/cdo-web/api/v2/stations"
        f"?datasetid=GHCND&extent={min_lat},{min_lon},{max_lat},{max_lon}&limit=1000"
    )

    headers = {"token": NCEI_TOKEN}

    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()

    data = r.json()
    return data.get("results", [])


def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

def sort_stations_by_distance(stations, lat, lon):
    for s in stations:
        slat = s["latitude"]
        slon = s["longitude"]
        s["distance_km"] = haversine(lat, lon, slat, slon)
    return sorted(stations, key=lambda x: x["distance_km"])

def filter_asos_awos(stations):
    """Return only GHCND stations that are ASOS/AWOS (USW prefix)."""
    filtered = []
    for s in stations:
        station_id = s["id"]  # e.g., "GHCND:USW00013743"
        if station_id.startswith("GHCND:USW"):
            filtered.append(s)
    return filtered

def get_ghcnd_stations_nearby(lat, lon):
    stations = get_ghcnd_stations(lat, lon)
    stations = filter_asos_awos(stations)
    stations = sort_stations_by_distance(stations, lat, lon)
    return stations

# -------------------------------------------------------------------
# Fetch all observations in a date range (with pagination)
# -------------------------------------------------------------------
NCEI_TOKEN = st.secrets["ncdc_api_key"]
NCEI_BASE = "https://www.ncei.noaa.gov/cdo-web/api/v2/data"

def get_ncei_daily_summary(station_id, start_date, end_date):
    headers = {"token": NCEI_TOKEN}

    start = start_date.strftime("%Y-%m-%d")
    end = end_date.strftime("%Y-%m-%d")

    all_results = []
    offset = 0
    limit = 1000

    while True:
        params = {
            "datasetid": "GHCND",
            "stationid": station_id,
            "startdate": start,
            "enddate": end,
            "units": "standard",
            "limit": limit,
            "offset": offset
        }

        r = requests.get(NCEI_BASE, headers=headers, params=params)
        r.raise_for_status()
        batch = r.json().get("results", [])

        if not batch:
            break

        all_results.extend(batch)
        offset += limit

    # Organize by date
    days = defaultdict(dict)

    for item in all_results:
        date = item["date"][:10]
        datatype = item["datatype"]
        value = item["value"]
        days[date][datatype] = value

    summaries = []
    for date, vals in sorted(days.items()):
        tmax = vals.get("TMAX")
        tmin = vals.get("TMIN")
        tavg = vals.get("TAVG")
        prcp = vals.get("PRCP")

        if tavg is None and tmax is not None and tmin is not None:
            tavg = (tmax + tmin) / 2

        summaries.append({
            "date": date,
            "avg_temp_f": tavg,
            "total_precip_in": prcp
        })

    print("Total raw results:", len(all_results))
    print("Total days parsed:", len(days))
    print("Total summaries:", len(summaries))


    return summaries
