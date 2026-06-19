import math
import requests
import numpy as np
import cv2
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
import pandas as pd
import folium
import os

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)

def pixel2deg(xtile, ytile, px, py, zoom, tile_size=256):
    n = 2.0 ** zoom
    x = xtile + (px / tile_size)
    y = ytile + (py / tile_size)
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)

def fetch_tile(x, y, z):
    url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        return img
    return None

def detect_pools(img, min_area=20):
    if img is None:
        return []
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_blue = np.array([80, 50, 50])
    upper_blue = np.array([130, 255, 255])
    mask = cv2.inRange(hsv, lower_blue, upper_blue)
    kernel = np.ones((3,3), np.uint8)
    mask = cv2.erode(mask, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=2)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    pools = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > min_area:
            x, y, w, h = cv2.boundingRect(cnt)
            pools.append({'px': x + w // 2, 'py': y + h // 2, 'area': area})
    return pools

def reverse_geocode(lat, lon, geolocator, retries=3):
    for _ in range(retries):
        try:
            location = geolocator.reverse(f"{lat}, {lon}", exactly_one=True, timeout=10)
            if location:
                return location.address
            return "Address not found"
        except GeocoderTimedOut:
            time.sleep(1)
        except Exception:
            return "Error finding address"
    return "Address not found (Timeout)"

def get_location_coordinates(location_name):
    """Geocodes a location name to its central latitude and longitude."""
    geolocator = Nominatim(user_agent="dengue_pool_detector_search")
    try:
        location = geolocator.geocode(location_name, timeout=10)
        if location:
            return location.latitude, location.longitude
        return None, None
    except Exception as e:
        print(f"Error fetching location coordinates: {e}")
        return None, None

def get_bounding_box(lat, lon, radius_km):
    """Calculates a bounding box around a coordinate given a radius in km."""
    # Approximate conversions: 1 deg lat ~ 111 km, 1 deg lon ~ 111 * cos(lat) km
    lat_offset = radius_km / 111.0
    lon_offset = radius_km / (111.0 * math.cos(math.radians(lat)))

    start_lat = lat + lat_offset # North
    end_lat = lat - lat_offset   # South
    start_lon = lon - lon_offset # West
    end_lon = lon + lon_offset   # East

    return start_lat, start_lon, end_lat, end_lon

def scan_area_yield(start_lat, start_lon, end_lat, end_lon, zoom=18):
    """Scans an area and yields progress and detected pools."""
    start_x, start_y = deg2num(start_lat, start_lon, zoom)
    end_x, end_y = deg2num(end_lat, end_lon, zoom)

    min_x, max_x = min(start_x, end_x), max(start_x, end_x)
    min_y, max_y = min(start_y, end_y), max(start_y, end_y)

    total_tiles_x = (max_x - min_x) + 1
    total_tiles_y = (max_y - min_y) + 1
    total_tiles = total_tiles_x * total_tiles_y

    # Put a hard limit to avoid scanning an entire state by accident
    if total_tiles > 2500:
        yield {"error": "Área de busca muito grande. Por favor, reduza o raio de busca."}
        return

    geolocator = Nominatim(user_agent="dengue_pool_detector_v1")
    detected_pools = []

    tiles_processed = 0
    for x in range(min_x, max_x + 1):
        for y in range(min_y, max_y + 1):
            img = fetch_tile(x, y, zoom)
            if img is not None:
                pools_in_tile = detect_pools(img)
                for pool in pools_in_tile:
                    pool_lat, pool_lon = pixel2deg(x, y, pool['px'], pool['py'], zoom)
                    address = reverse_geocode(pool_lat, pool_lon, geolocator)
                    pool_data = {
                        'Latitude': pool_lat,
                        'Longitude': pool_lon,
                        'Address': address
                    }
                    detected_pools.append(pool_data)
            tiles_processed += 1
            progress = tiles_processed / total_tiles
            yield {"progress": progress, "pools": detected_pools}
            time.sleep(0.05)

    yield {"done": True, "pools": detected_pools}

def generate_reports(pools_data, output_dir="output"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if not pools_data:
        return None, None

    df = pd.DataFrame(pools_data)
    csv_path = os.path.join(output_dir, "detected_pools.csv")
    df.to_csv(csv_path, index=False)

    center_lat = df['Latitude'].mean()
    center_lon = df['Longitude'].mean()

    m = folium.Map(location=[center_lat, center_lon], zoom_start=17, tiles="OpenStreetMap")
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', name='Esri Satellite', overlay=False, control=True
    ).add_to(m)

    for _, row in df.iterrows():
        popup_html = f"<b>Address:</b> {row['Address']}<br><b>Coords:</b> {row['Latitude']:.5f}, {row['Longitude']:.5f}"
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color="red", icon="tint")
        ).add_to(m)

    folium.LayerControl().add_to(m)
    map_path = os.path.join(output_dir, "pools_map.html")
    m.save(map_path)

    return csv_path, m

if __name__ == "__main__":
    lat1, lon1 = -23.584, -46.666
    lat2, lon2 = -23.585, -46.665
    print("Starting pool detection scan...")
    pools = []
    for update in scan_area_yield(lat1, lon1, lat2, lon2):
        if "done" in update:
            pools = update["pools"]
            break
    print(f"\nScan complete. Total pools detected: {len(pools)}")
    generate_reports(pools)
