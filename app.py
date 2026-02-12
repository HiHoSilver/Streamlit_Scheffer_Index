from datetime import datetime
import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from noaa_api import get_ghcnd_stations_nearby, get_ncei_daily_summary
from processing import process_data

st.set_page_config(layout="wide")
st.title("Nearest Weather Stations (NCEI GHCND)")

# -----------------------------
# Session State Initialization
# -----------------------------
if "marker" not in st.session_state:
    st.session_state.marker = None

if "last_coords" not in st.session_state:
    st.session_state.last_coords = None

if "address_to_geocode" not in st.session_state:
    st.session_state.address_to_geocode = None

if "stations" not in st.session_state:
    st.session_state.stations = None

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.write("**1. Select Location**")
    address = st.text_input("Enter an address:")
    locate_address = st.button("Locate Address")

    st.write("**2. Find Weather Stations**")
    nearest_station = st.button("Find nearest GHCND stations")

    if st.session_state.stations:
        st.write("**3. Select Weather Station**")

        stations_dict = {}
        for idx, s in enumerate(st.session_state.stations[:5], start=1):
            name = s["name"]
            dist_mi = s["distance_km"] * 0.621371
            station_key = f"{idx}. {name} — {dist_mi:.2f} mi"
            stations_dict[station_key] = s["id"]

        select_station = st.selectbox("Select Station", list(stations_dict.keys()))
        st.write("Selected:", stations_dict.get(select_station))

        st.write("**4. Select Year**")
        current_year = datetime.now().year
        year_list = [current_year - i for i in range(1, 5)]
        select_year = st.selectbox("Year", year_list)

        get_data = st.button("Get Data")

# -----------------------------
# Address Geocoding
# -----------------------------
if locate_address:
    st.session_state.address_to_geocode = address

geolocator = Nominatim(user_agent="streamlit_app")

center_lat, center_lng = 39.8283, -98.5795  # default

if st.session_state.address_to_geocode:
    location = geolocator.geocode(st.session_state.address_to_geocode)
    if location:
        st.session_state.marker = {
            "lat": location.latitude,
            "lng": location.longitude,
            "popup": location.address
        }
        st.session_state.last_coords = (location.latitude, location.longitude)
        center_lat, center_lng = location.latitude, location.longitude
        st.session_state.stations = None
        st.success(f"Address found: {location.address}")
    else:
        st.error("Address not found.")

    st.session_state.address_to_geocode = None

# -----------------------------
# Station Lookup
# -----------------------------
if nearest_station and st.session_state.last_coords:
    lat, lng = st.session_state.last_coords
    st.session_state.stations = get_ghcnd_stations_nearby(lat, lng)
    st.rerun()

# -----------------------------
# Layout Columns
# -----------------------------
col1, col2 = st.columns([0.3, 0.7], gap="large")

# -----------------------------
# Station List
# -----------------------------
with col1:
    if st.session_state.last_coords and st.session_state.stations:
        st.write("**Nearest GHCND Stations:**")
        for idx, s in enumerate(st.session_state.stations[:5], start=1):
            name = s["name"]
            station_id = s["id"]
            dist_mi = s["distance_km"] * 0.621371
            elevation = s.get("elevation", "N/A")

            st.markdown(
                f"""
                **{idx}. {name}** ({station_id})  
                • Elevation: {elevation} m  
                • Distance: {dist_mi:.2f} miles  
                """
            )
    else:
        st.write("*Stations will appear here after selecting a location.*")

# -----------------------------
# Map
# -----------------------------
if st.session_state.marker:
    center_lat = st.session_state.marker["lat"]
    center_lng = st.session_state.marker["lng"]

m = folium.Map(location=[center_lat, center_lng], zoom_start=4)
bounds = []

# Main marker
if st.session_state.marker:
    lat0 = st.session_state.marker["lat"]
    lng0 = st.session_state.marker["lng"]
    folium.Marker(
        [lat0, lng0],
        popup=st.session_state.marker["popup"],
        icon=folium.Icon(color="blue")
    ).add_to(m)
    bounds.append([lat0, lng0])

# Station markers
if st.session_state.stations:
    for idx, s in enumerate(st.session_state.stations[:5], start=1):
        lat = s["latitude"]
        lon = s["longitude"]
        name = s["name"]
        station_id = s["id"]
        dist_mi = s["distance_km"] * 0.621371

        popup_text = f"{name} ({station_id}) — {dist_mi:.2f} mi"

        icon_html = (
            f'<div style="font-size:14px;color:white;background:#0078ff;'
            'border-radius:50%;width:24px;height:24px;display:flex;'
            'align-items:center;justify-content:center;border:2px solid white;">'
            f'{idx}</div>'
        )

        folium.Marker(
            [lat, lon],
            icon=folium.DivIcon(html=icon_html),
            popup=popup_text
        ).add_to(m)

        bounds.append([lat, lon])

if st.session_state.stations and len(bounds) > 1:
    m.fit_bounds(bounds)

with col2:
    map_data = st_folium(
        m,
        width=700,
        height=500,
        key="folium_map",
        returned_objects=["last_clicked"]
    )

# -----------------------------
# Handle Map Click
# -----------------------------
if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lng = map_data["last_clicked"]["lng"]

    st.session_state.marker = {"lat": lat, "lng": lng, "popup": "Clicked Location"}
    st.session_state.last_coords = (lat, lng)
    st.session_state.stations = None

# -----------------------------
# Show Coordinates
# -----------------------------
if st.session_state.last_coords:
    lat, lng = st.session_state.last_coords
    st.success(f"Current Coordinates: {lat}, {lng}")

# -----------------------------
# Fetch Data
# -----------------------------
if st.session_state.stations and get_data:
    ghcnd_id = stations_dict.get(select_station)
    start_dt = datetime(select_year, 1, 1)
    end_dt = datetime(select_year, 12, 31)

    summaries = get_ncei_daily_summary(ghcnd_id, start_dt, end_dt)
    print(summaries[0])
    df, data_completion_pct = process_data(summaries)
    st.dataframe(df, hide_index=True)
    st.write(f"Amount of Data Available for {select_station[2:]} for {select_year}: {data_completion_pct}%")

    st.latex(r'''
        Index =
        \sum_{Jan}^{Dec} [(T-35)(D-3)]/30
    ''')
