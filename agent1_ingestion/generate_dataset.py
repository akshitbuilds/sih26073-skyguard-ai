import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# Match the exact stations used in the rest of your pipeline
STATIONS = [
    {"station_id": "AWS_SANTACRUZ", "name": "Santacruz", "lat": 19.08, "lon": 72.85, "elev": 9},
    {"station_id": "AWS_COLABA",     "name": "Colaba",    "lat": 18.91, "lon": 72.81, "elev": 11},
    {"station_id": "AWS_BKC",        "name": "BKC",       "lat": 19.06, "lon": 72.86, "elev": 6},
    {"station_id": "AWS_THANE",      "name": "Thane",     "lat": 19.20, "lon": 72.96, "elev": 23},
    {"station_id": "AWS_BYCULLA",    "name": "Byculla",   "lat": 18.97, "lon": 72.83, "elev": 10},
]


url = "https://archive-api.open-meteo.com/v1/archive"
all_station_data = []

for station in STATIONS:
    print(f"Fetching official data for {station['station_id']}...")
    
    params = {
        "latitude": station["lat"],
        "longitude": station["lon"],
        "start_date": "2005-06-22",
        "end_date": "2005-08-18",
        "hourly": ["temperature_2m", "relative_humidity_2m", "surface_pressure"]
    }

    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]

    # Process hourly data
    hourly = response.Hourly()
    temps = hourly.Variables(0).ValuesAsNumpy()
    humidities = hourly.Variables(1).ValuesAsNumpy()
    pressures = hourly.Variables(2).ValuesAsNumpy()

    dates = pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left"
    )

    # Format dataframe matching schema.json expected by fault_injector.py and replay.py
    df_station = pd.DataFrame({
        "station_id": station["station_id"],
        "timestamp": dates.strftime('%Y-%m-%dT%H:%M:%S'),
        "temp": [round(t, 2) for t in temps],
        "pressure": [round(p, 2) for p in pressures],
        "humidity": [round(h, 2) for h in humidities],
        "lat": station["lat"],
        "lon": station["lon"]
    })
    
    all_station_data.append(df_station)

# Combine all stations into a single DataFrame
final_clean_df = pd.concat(all_station_data, ignore_index=True)

# Save directly as clean_dataset.csv so fault_injector.py can read it seamlessly
output_filename = "clean_dataset.csv"
final_clean_df.to_csv(output_filename, index=False)
print(f"Wrote {output_filename} successfully. Ready for fault_injector.py.")
