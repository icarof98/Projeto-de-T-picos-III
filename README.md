# Dengue Pool Detector

This application helps Dengue Control teams identify potential mosquito breeding grounds by detecting swimming pools in satellite imagery. It uses computer vision to find the characteristic blue/cyan color of pools, calculates their geographic coordinates, and generates an actionable report and interactive map.

## Methodology

1. **Satellite Imagery Fetching**: The script fetches high-resolution satellite imagery tiles from the Esri World Imagery map service for a given geographic bounding box.
2. **Computer Vision (OpenCV)**: Each image tile is converted into the HSV color space. A color thresholding mask is applied to isolate pixels that fall within the typical blue/cyan range of swimming pools. Morphological operations (erosion and dilation) are used to clean up noise. Contours are then found to identify individual pool areas.
3. **Coordinate Calculation**: The pixel coordinates of the detected pools within the local image tile are translated back into global geographic coordinates (Latitude and Longitude) using the standard Web Mercator projection formulas.
4. **Reverse Geocoding**: The calculated geographic coordinates are passed to Nominatim (via `geopy`) to retrieve the approximate street address for the location.
5. **Output Generation**: The results are exported to a CSV file (`detected_pools.csv`) and an interactive HTML map (`pools_map.html`) using `folium`.

## Prerequisites

Python 3.x is required. Install the necessary dependencies using pip:

```bash
pip install requests opencv-python-headless numpy geopy folium pandas
```

## Usage

1. Open `dengue_pool_detector.py`.
2. Modify the target bounding box coordinates at the bottom of the script in the `__main__` block:
   ```python
   # Example bounding box
   lat1, lon1 = -23.584, -46.666
   lat2, lon2 = -23.585, -46.665
   ```
3. Run the script:
   ```bash
   python dengue_pool_detector.py
   ```
4. The output files will be generated in the `output/` directory:
   - `output/detected_pools.csv`: Contains the latitude, longitude, address, and tile info.
   - `output/pools_map.html`: An interactive map plotting the detected locations.
