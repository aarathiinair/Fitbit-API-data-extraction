import base64
import requests
import pandas as pd
import json
import os
from urllib.parse import urlencode
from datetime import datetime, timedelta
import pytz

# Define constants
CLIENT_ID = '23PHMD'
CLIENT_SECRET = '0ce3a7d7167a733fd9a3b5c23a3438f6'
REDIRECT_URI = 'http://127.0.0.1:8080/'
TOKEN_URL = 'https://api.fitbit.com/oauth2/token'
API_URL = 'https://api.fitbit.com/1/user/-/ecg/list.json'
TOKEN_FILE = 'fitbit_tokens.json'

def save_tokens(tokens):
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f)

def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    return None

def get_new_access_token():
    while True:
        authorization_code = input("Enter the authorization code: ")
        data = {
            'client_id': CLIENT_ID,
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'code': authorization_code,
        }
        headers = {
            'Authorization': 'Basic ' + base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode(),
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            response = requests.post(TOKEN_URL, headers=headers, data=urlencode(data))
            response.raise_for_status()
            tokens = response.json()
            save_tokens(tokens)
            return tokens['access_token']
        except requests.exceptions.HTTPError as e:
            print(f"Error: {e}")
            print("Response content:", response.text)
            print("Please check the following:")
            print("1. Ensure the authorization code is correct and hasn't expired.")
            print("2. Verify that CLIENT_ID, CLIENT_SECRET, and REDIRECT_URI match your Fitbit application settings.")
            print("3. Make sure you're using the correct authorization URL to generate the code.")
            retry = input("Do you want to try again? (y/n): ")
            if retry.lower() != 'y':
                raise Exception("Failed to obtain access token") from e

def refresh_access_token(refresh_token):
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': 'Basic ' + base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()
    }

    response = requests.post(TOKEN_URL, headers=headers, data=urlencode(data))
    
    if response.status_code == 400 and 'invalid_grant' in response.text:
        print("Invalid refresh token. Obtaining new authorization code.")
        return get_new_access_token()
    
    response.raise_for_status()
    tokens = response.json()
    save_tokens(tokens)
    return tokens['access_token']

def get_valid_access_token():
    tokens = load_tokens()
    if not tokens:
        return get_new_access_token()
    
    access_token = tokens['access_token']
    response = requests.get(API_URL, headers={'Authorization': f'Bearer {access_token}'})
    
    if response.status_code == 401:
        print("Access token expired. Refreshing...")
        return refresh_access_token(tokens['refresh_token'])
    
    return access_token

def get_device_info(access_token):
    url = "https://api.fitbit.com/1/user/-/devices.json"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        devices = response.json()
        if devices:
            # Return the ID of the first device (you might want to modify this if there are multiple devices)
            return devices[0]['id']
    return None

def fetch_ecg_data(access_token, date, sort='asc', limit=10, offset=0):
    all_readings = []
    fitbit_timezone = pytz.utc
    local_timezone = pytz.timezone('Asia/Kolkata')

    start_date = local_timezone.localize(datetime.strptime(date, '%Y-%m-%d')).astimezone(fitbit_timezone)
    end_date = start_date + timedelta(days=1)

    while True:
        params = {
            'afterDate': start_date.strftime('%Y-%m-%dT%H:%M:%S'),
            'sort': sort,
            'limit': limit,
            'offset': offset
        }
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }

        response = requests.get(API_URL, headers=headers, params=params)
        
        if response.status_code == 401:
            print("Access token expired during data fetch. Refreshing...")
            access_token = get_valid_access_token()
            headers['Authorization'] = f'Bearer {access_token}'
            response = requests.get(API_URL, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error: Received status code {response.status_code}")
            print(f"Response: {response.text}")
            break

        data = response.json()
        print(f"Raw API Response: {json.dumps(data, indent=2)}")
        ecg_readings = data.get('ecgReadings', [])
        if not ecg_readings:
            print(f"No ECG data found for {date}")
            break
        
        ecg_readings = [reading for reading in ecg_readings if start_date <= datetime.strptime(reading['startTime'], '%Y-%m-%dT%H:%M:%S.%f').replace(tzinfo=pytz.utc) < end_date]
        all_readings.extend(ecg_readings)
        
        if len(ecg_readings) < limit:
            break
        
        offset += limit

    return all_readings

def save_ecg_data_to_csv(device_id, readings, date):
    if not readings:
        print(f"No ECG data found for {date}")
        return

    data = []
    for reading in readings:
        start_time = datetime.strptime(reading['startTime'], '%Y-%m-%dT%H:%M:%S.%f').replace(tzinfo=pytz.utc)
        scaling_factor = reading['scalingFactor']
        sampling_frequency = reading['samplingFrequencyHz']
        
        for i, sample in enumerate(reading['waveformSamples']):
            timestamp = start_time + timedelta(seconds=i / sampling_frequency)
            data.append({
                'Device ID': device_id,
                'Timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S.%f'),
                'ECG Voltage (mV)': sample / scaling_factor
            })
    
    df = pd.DataFrame(data)
    output_path = f'ecg_data_{date}.csv'
    df.to_csv(output_path, index=False)
    print(f"ECG data for {date} saved to {output_path}")

def main():
    date = input("Enter the date in format yyyy-MM-dd: ")
    try:
        access_token = get_valid_access_token()
        device_id = get_device_info(access_token)
        if not device_id:
            print("Failed to retrieve device information. Using 'Unknown' as device ID.")
            device_id = "Unknown"
        ecg_data = fetch_ecg_data(access_token, date)
        save_ecg_data_to_csv(device_id, ecg_data, date)
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please check your Fitbit application settings and try again.")

if __name__ == '__main__':
    main()