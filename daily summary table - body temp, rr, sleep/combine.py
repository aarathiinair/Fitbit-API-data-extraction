import base64
import requests
import pandas as pd
import json
import os
from urllib.parse import urlencode
from datetime import datetime, timedelta

CLIENT_ID = '23PHMD'
CLIENT_SECRET = '0ce3a7d7167a733fd9a3b5c23a3438f6'
REDIRECT_URI = 'http://127.0.0.1:8080/'
TOKEN_URL = 'https://api.fitbit.com/oauth2/token'
SLEEP_API_URL = 'https://api.fitbit.com/1.2/user/-/sleep/date/'
BR_API_URL = 'https://api.fitbit.com/1/user/-/br/date/'
TEMP_API_URL = 'https://api.fitbit.com/1/user/-/temp/skin/date/'
DEVICES_API_URL = 'https://api.fitbit.com/1/user/-/devices.json'
TOKEN_FILE = 'fitbit_tokens.json'

def save_tokens(tokens):
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f)

def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    return None

def get_new_tokens():
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
   
    response = requests.post(TOKEN_URL, headers=headers, data=urlencode(data))
    response.raise_for_status()
    tokens = response.json()
    tokens['expires_in'] = 28800  # Manually add expires_in
    save_tokens(tokens)
    return tokens['access_token']

def fetch_device_id(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    response = requests.get(DEVICES_API_URL, headers=headers)
    response.raise_for_status()
    devices = response.json()
    if devices:
        return devices[0]['id']  # Return the ID of the first device
    return None

def refresh_access_token():
    tokens = load_tokens()
    if not tokens or 'refresh_token' not in tokens:
        print("No refresh token available. Requesting new tokens.")
        return get_new_tokens()
   
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': tokens['refresh_token'],
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
   
    response = requests.post(TOKEN_URL, headers=headers, data=urlencode(data))
    print("Refresh Token Response Status Code:", response.status_code)
    print("Refresh Token Response Content:", response.content)
   
    if response.status_code == 400 and 'invalid_grant' in response.json().get('errors', [{}])[0].get('message', ''):
        print("Refresh token is invalid. Requesting new authorization code.")
        return get_new_tokens()
   
    response.raise_for_status()
    tokens = response.json()
    tokens['expires_in'] = 28800  # Manually add expires_in
    save_tokens(tokens)
    return tokens['access_token']

def get_valid_access_token():
    tokens = load_tokens()
    if not tokens or 'access_token' not in tokens:
        return get_new_tokens()
   
    if tokens.get('expires_in', 0) < 60:
        return refresh_access_token()
   
    return tokens['access_token']

def fetch_data(url, date):
    try:
        access_token = get_valid_access_token()
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
        # Fix for breathing rate API
        if 'br' in url:
            full_url = f"{url}{date}/all.json"
        else:
            full_url = f"{url}{date}.json"
        
        response = requests.get(full_url, headers=headers)
        print(f"Initial Response Status Code for {url}: {response.status_code}")
        if response.status_code == 401:
            access_token = refresh_access_token()
            headers['Authorization'] = f'Bearer {access_token}'
            response = requests.get(full_url, headers=headers)
       
        print(f"Final Response Status Code for {url}: {response.status_code}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        if response.status_code == 401:
            print("Unauthorized request. Retrying with new authorization code.")
            access_token = get_new_tokens()
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            response = requests.get(full_url, headers=headers)
            response.raise_for_status()
            return response.json()
        else:
            print(f"Failed to fetch data from {url}. Returning None.")
            return None
    except Exception as err:
        print(f"An error occurred: {err}")
        return None

def process_sleep_data(sleep_data):
    if not sleep_data or not sleep_data.get('sleep'):
        print("No sleep data found.")
        return {}

    sleep = sleep_data['sleep'][0]
    summary = sleep_data['summary']

    end_time = datetime.strptime(sleep['endTime'], "%Y-%m-%dT%H:%M:%S.%f").strftime("%H:%M")
    start_time = datetime.strptime(sleep['startTime'], "%Y-%m-%dT%H:%M:%S.%f").strftime("%H:%M")

    sleep_dict = {
        'date': sleep['dateOfSleep'],
        'duration of sleep (in milliseconds)': sleep['duration'],
        'sleep efficiency score': sleep['efficiency'],
        'startTime of sleep': start_time,
        'endTime of sleep': end_time,
        'sleep infoCode': sleep.get('infoCode', ''),
        'isMainSleep': sleep['isMainSleep'],
        'logId': sleep['logId'],
        'minutesAfterWakeup': sleep['minutesAfterWakeup'],
        'minutesAsleep': sleep['minutesAsleep'],
        'minutesAwake': sleep['minutesAwake'],
        'minutesToFallAsleep': sleep['minutesToFallAsleep'],
        'sleep logType': sleep['logType'],
        'timeInBed (in minutes)': sleep['timeInBed'],
        'type': sleep['type']
    }

    if sleep['type'] == 'stages' and 'levels' in sleep:
        stages_data = sleep['levels'].get('data', [])
        for stage in ['deep', 'light', 'rem', 'wake']:
            sleep_dict[f'{stage}_count'] = 0
            sleep_dict[f'{stage}_seconds'] = 0
            sleep_dict[f'{stage}_minutes'] = 0
            sleep_dict[f'{stage}_thirtyDayAvgMinutes'] = ''

        for entry in stages_data:
            stage = entry['level']
            sleep_dict[f'{stage}_count'] += 1
            sleep_dict[f'{stage}_seconds'] += entry['seconds']
            sleep_dict[f'{stage}_minutes'] += entry['seconds'] // 60

        summary_stages = sleep['levels'].get('summary', {})
        for stage in ['deep', 'light', 'rem', 'wake']:
            if stage in summary_stages:
                sleep_dict[f'{stage}_count'] = summary_stages[stage]['count']
                sleep_dict[f'{stage}_minutes'] = summary_stages[stage]['minutes']
                sleep_dict[f'{stage}_thirtyDayAvgMinutes'] = summary_stages[stage].get('thirtyDayAvgMinutes', '')

        short_data = sleep['levels'].get('shortData', [])
        sleep_dict['shortData_dateTime'] = short_data[0]['dateTime'] if short_data else ''
        sleep_dict['shortData_dateTimeTimestamp'] = short_data[-1]['dateTime'] if short_data else ''

    # Add summary data
    sleep_dict.update({
        'totalMinutesAsleep (in minutes)': summary['totalMinutesAsleep'],
        'totalSleepRecords': summary['totalSleepRecords'],
        'totalTimeInBed (in minutes)': summary['totalTimeInBed']
    })

    return sleep_dict

def process_breathing_rate_data(br_data):
    if not br_data or not br_data.get('br'):
        print("No breathing rate data found.")
        return {}

    br = br_data['br'][0]
    return {
        'light_sleep_breathing_rate (in breaths per minute)': br['value']['lightSleepSummary']['breathingRate'],
        'deep_sleep_breathing_rate (in breaths per minute)': br['value']['deepSleepSummary']['breathingRate'],
        'rem_sleep_breathing_rate (in breaths per minute)': br['value']['remSleepSummary']['breathingRate'],
        'full_sleep_breathing_rate (in breaths per minute)': br['value']['fullSleepSummary']['breathingRate']
    }

def process_temperature_data(temp_data):
    if not temp_data or not temp_data.get('tempSkin'):
        print("No temperature data found.")
        return {}

    temp = temp_data['tempSkin'][0]
    return {
        'nightly_relative_temperature_change': temp['value']['nightlyRelative']
    }

def save_combined_data_to_csv(date, sleep_data, br_data, temp_data, filename):
    combined_data = process_sleep_data(sleep_data) if sleep_data else {}
    if br_data:
        combined_data.update(process_breathing_rate_data(br_data))
    if temp_data:
        combined_data.update(process_temperature_data(temp_data))

    # Fetch device ID
    access_token = get_valid_access_token()
    device_id = fetch_device_id(access_token)

    # Add device ID as the first column
    combined_data = {'device_id': device_id, **combined_data}

    df = pd.DataFrame([combined_data])
    df.to_csv(filename, index=False)
    print(f"Combined data saved to {filename}")
    
def main():
    date = input("Enter the date in format yyyy-MM-dd: ")
    sleep_data = fetch_data(SLEEP_API_URL, date)
    br_data = fetch_data(BR_API_URL, date)
    temp_data = fetch_data(TEMP_API_URL, date)

    csv_filename = f'combined_fitbit_data_{date}.csv'
    save_combined_data_to_csv(date, sleep_data, br_data, temp_data, csv_filename)

if __name__ == '__main__':
    main()