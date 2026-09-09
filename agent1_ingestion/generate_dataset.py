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
    {"station_id": "AWS_001", "lat": 28.61, "lon": 77.21},  # Delhi
    {"station_id": "AWS_002", "lat": 19.08, "lon": 72.88},  # Mumbai
    {"station_id": "AWS_003", "lat": 13.08, "lon": 80.27},  # Chennai
    {"station_id": "AWS_004", "lat": 22.57, "lon": 88.36},  # Kolkata
    {"station_id": "AWS_005", "lat": 12.97, "lon": 77.59},  # Bengaluru
]

url = "https://archive-api.open-meteo.com/v1/archive"
all_station_data = []

for station in STATIONS:
    print(f"Fetching official data for {station['station_id']}...")
    
    params = {
        "latitude": station["lat"],
        "longitude": station["lon"],
        "start_date": "2023-05-22",
        "end_date": "2023-08-18",
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