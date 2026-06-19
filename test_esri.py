import requests
url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/18/100000/100000"
response = requests.get(url)
print(response.status_code)
print(response.headers['Content-Type'])
