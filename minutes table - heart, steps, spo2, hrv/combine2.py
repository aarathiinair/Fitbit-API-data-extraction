import requests
import base64
import json
import datetime
import csv
import os
from urllib.parse import urlencode
import logging


# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Fitbit API credentials
CLIENT_ID = '23PHMD'
CLIENT_SECRET = '0ce3a7d7167a733fd9a3b5c23a3438f6'
REDIRECT_URI = 'http://127.0.0.1:8080/'
TOKEN_FILE = 'fitbit_tokens.json'

# Save tokens to a file
def save_tokens(access_token, refresh_token):
    tokens = {
        "access_token": access_token,
        "refresh_token": refresh_token
    }
    with open(TOKEN_FILE, 'w') as token_file:
        json.dump(tokens, token_file)
    logging.info(f"Tokens saved to {TOKEN_FILE}")

# Load tokens from a file
def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as token_file:
            tokens = json.load(token_file)
            return tokens.get("access_token"), tokens.get("refresh_token")
    return None, None

# Refresh the access token using the refresh token
def refresh_access_token(client_id, client_secret, refresh_token):
    token_url = "https://api.fitbit.com/oauth2/token"
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{client_id}:{client_secret}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    body = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    response = requests.post(token_url, headers=headers, data=body)
    response_json = response.json()
    logging.debug("Refresh Token Response: %s", response_json)
    if "access_token" in response_json and "refresh_token" in response_json:
        save_tokens(response_json["access_token"], response_json["refresh_token"])
        return response_json["access_token"], response_json["refresh_token"]
    else:
        logging.error("Error: No access token or refresh token found in the response.")
        return None, None

# Check and refresh tokens if necessary
def check_and_refresh_tokens():
    access_token, refresh_token = load_tokens()
    if not access_token or not refresh_token:
        logging.warning("No tokens found. Please run the initial authorization process.")
        return None, None

    return refresh_access_token(CLIENT_ID, CLIENT_SECRET, refresh_token)

# Obtain new tokens using authorization code
def get_new_tokens():
    AUTHORIZATION_CODE = input("Enter the authorization code: ")
    token_url = "https://api.fitbit.com/oauth2/token"
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    body = {
        "client_id": CLIENT_ID,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code": AUTHORIZATION_CODE
    }
    response = requests.post(token_url, headers=headers, data=urlencode(body))
    response_json = response.json()
    logging.debug("Token Response: %s", response_json)

    if "access_token" in response_json and "refresh_token" in response_json:
        save_tokens(response_json["access_token"], response_json["refresh_token"])
        return response_json["access_token"], response_json["refresh_token"]
    else:
        logging.error("Error: Unable to retrieve tokens.")
        return None, None

# Get activity intraday data from Fitbit API
def get_activity_intraday_data(access_token, resource, date, start_time=None, end_time=None, detail_level='1min'):
    base_url = f"https://api.fitbit.com/1/user/-/activities/{resource}/date/{date}/1d/{detail_level}"
    if start_time and end_time:
        url = f"{base_url}/time/{start_time}/{end_time}.json"
    else:
        url = f"{base_url}.json"
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    logging.debug(f"Requesting activity data: {url}")
    response = requests.get(url, headers=headers)
    logging.debug(f"Activity Intraday Data Response Status Code: {response.status_code}")
    if response.status_code == 200:
        response_json = response.json()
        logging.debug(f"Activity Intraday Data Response: {json.dumps(response_json, indent=2)}")
        return response_json
    else:
        logging.error(f"Error: {response.status_code} - {response.text}")
        return None

# Get heart rate intraday data from Fitbit API
def get_heart_rate_intraday_data(access_token, date, start_time=None, end_time=None, detail_level='1min'):
    base_url = f"https://api.fitbit.com/1/user/-/activities/heart/date/{date}/1d/{detail_level}"
    if start_time and end_time:
        url = f"{base_url}/time/{start_time}/{end_time}.json"
    else:
        url = f"{base_url}.json"
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    logging.debug(f"Requesting heart rate data: {url}")
    response = requests.get(url, headers=headers)
    logging.debug(f"Heart Rate Intraday Data Response Status Code: {response.status_code}")
    if response.status_code == 200:
        response_json = response.json()
        logging.debug(f"Heart Rate Intraday Data Response: {json.dumps(response_json, indent=2)}")
        return response_json
    else:
        logging.error(f"Error: {response.status_code} - {response.text}")
        return None

# Get SpO2 intraday data
def get_spo2_intraday_data(access_token, date):
    url = f"https://api.fitbit.com/1/user/-/spo2/date/{date}/all.json"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Accept-Language": "en_US"
    }
    logging.debug(f"Requesting SpO2 data: {url}")
    response = requests.get(url, headers=headers)
    logging.debug(f"SpO2 Intraday Data Response Status Code: {response.status_code}")
    if response.status_code == 200:
        response_json = response.json()
        logging.debug(f"SpO2 Intraday Data Response: {json.dumps(response_json, indent=2)}")
        return response_json
    else:
        logging.error(f"Error: {response.status_code} - {response.text}")
        return None

# Get device information
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


def get_hrv_intraday_data(access_token, date):
    url = f"https://api.fitbit.com/1/user/-/hrv/date/{date}/all.json"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    logging.debug(f"Requesting HRV data: {url}")
    response = requests.get(url, headers=headers)
    logging.debug(f"HRV Intraday Data Response Status Code: {response.status_code}")
    if response.status_code == 200:
        response_json = response.json()
        logging.debug(f"HRV Intraday Data Response: {json.dumps(response_json, indent=2)}")
        return response_json
    else:
        logging.error(f"Error: {response.status_code} - {response.text}")
        return None


# Save combined data to a CSV file
def save_combined_data_to_csv(device_id, steps_data, heart_rate_data, spo2_data, hrv_data, start_date, end_date, filename):
    try:
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['device_id', 'date', 'time', 'steps', 'heart_rate', 'spo2', 'rmssd', 'coverage', 'hf', 'lf']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            start_datetime = datetime.datetime.strptime(f"{start_date} 22:00", "%Y-%m-%d %H:%M")
            end_datetime = datetime.datetime.strptime(f"{end_date} 22:00", "%Y-%m-%d %H:%M")
            
            # Process steps data
            steps_dict = {(entry['date'], entry['time'][:5]): entry['value'] for entry in steps_data}
            
            # Process heart rate data
            heart_dict = {(entry['date'], entry['time'][:5]): entry['value'] for entry in heart_rate_data}
            
            # Process SpO2 data
            spo2_dict = {}
            for date, data in spo2_data.items():
                if data and 'minutes' in data:
                    for entry in data['minutes']:
                        time = entry['minute'].split('T')[1][:5]
                        spo2_dict[(date, time)] = entry['value']
            
            # Process HRV data
            hrv_dict = {}
            for date, data in hrv_data.items():
                if data and 'hrv' in data:
                    for entry in data['hrv']:
                        for minute_data in entry['minutes']:
                            time = datetime.datetime.strptime(minute_data['minute'], '%Y-%m-%dT%H:%M:%S.%f').strftime('%H:%M')
                            hrv_dict[(date, time)] = {
                                'rmssd': minute_data['value']['rmssd'],
                                'coverage': minute_data['value']['coverage'],
                                'hf': minute_data['value']['hf'],
                                'lf': minute_data['value']['lf']
                            }
            
            current_time = start_datetime
            while current_time <= end_datetime:
                date_str = current_time.strftime("%Y-%m-%d")
                time_str = current_time.strftime("%H:%M")
                
                hrv_values = hrv_dict.get((date_str, time_str), {})
                
                row = {
                    'device_id': device_id,
                    'date': date_str,
                    'time': time_str,
                    'steps': steps_dict.get((date_str, time_str), ''),
                    'heart_rate': heart_dict.get((date_str, time_str), ''),
                    'spo2': spo2_dict.get((date_str, time_str), ''),
                    'rmssd': hrv_values.get('rmssd', ''),
                    'coverage': hrv_values.get('coverage', ''),
                    'hf': hrv_values.get('hf', ''),
                    'lf': hrv_values.get('lf', '')
                }
                writer.writerow(row)
                
                current_time += datetime.timedelta(minutes=1)
            
        logging.info(f"Combined data saved to {filename}")
    except Exception as e:
        logging.error(f"Failed to save combined data: {e}")
        alternate_filename = os.path.join(os.path.expanduser('~'), 'Downloads', os.path.basename(filename))
        logging.info(f"Attempting to save the data to an alternate location: {alternate_filename}")
        try:
            # Repeat the same process for the alternate location
            with open(alternate_filename, 'w', newline='') as csvfile:
                fieldnames = ['device_id', 'date', 'time', 'steps', 'heart_rate', 'spo2']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                current_time = start_datetime
                while current_time <= end_datetime:  # Changed < to <= to include the final 22:00 timestamp
                    date_str = current_time.strftime("%Y-%m-%d")
                    time_str = current_time.strftime("%H:%M")
                    
                    row = {
                        'device_id': device_id,
                        'date': date_str,
                        'time': time_str,
                        'steps': steps_dict.get((date_str, time_str), ''),
                        'heart_rate': heart_dict.get((date_str, time_str), ''),
                        'spo2': spo2_dict.get((date_str, time_str), '')
                    }
                    writer.writerow(row)
                    
                    current_time += datetime.timedelta(minutes=1)
                
            logging.info(f"Combined data saved to {alternate_filename}")
        except Exception as e:
            logging.error(f"Failed to save combined data to alternate location: {e}")
            

def sanitize_filename(filename):
    return filename.replace(':', '-')

if __name__ == "__main__":
    # Load tokens or get new tokens if none are found
    ACCESS_TOKEN, REFRESH_TOKEN = load_tokens()
    if not ACCESS_TOKEN or not REFRESH_TOKEN:
        ACCESS_TOKEN, REFRESH_TOKEN = get_new_tokens()
        if not ACCESS_TOKEN or not REFRESH_TOKEN:
            logging.error("Failed to obtain new tokens. Exiting.")
            exit(1)

    # Refresh tokens if necessary
    ACCESS_TOKEN, REFRESH_TOKEN = check_and_refresh_tokens()
    if not ACCESS_TOKEN or not REFRESH_TOKEN:
        ACCESS_TOKEN, REFRESH_TOKEN = get_new_tokens()
        if not ACCESS_TOKEN or not REFRESH_TOKEN:
            logging.error("Failed to refresh or obtain new tokens. Exiting.")
            exit(1)

    # Get device information
    device_id = get_device_info(ACCESS_TOKEN)
    if not device_id:
        logging.warning("Failed to retrieve device information. Using 'Unknown' as device ID.")
        device_id = "Unknown"

    # Get user input for date
    date_input = input("Enter the date (YYYY-MM-DD): ")
    
    

    try:
        input_date = datetime.datetime.strptime(date_input, "%Y-%m-%d")
        next_day = (input_date + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        
        current_directory = os.getcwd()
        
        # Fetch steps data for both days
        steps_data = []
        for date in [date_input, next_day]:
            steps_response = get_activity_intraday_data(ACCESS_TOKEN, 'steps', date)
            if steps_response and 'activities-steps-intraday' in steps_response:
                for entry in steps_response['activities-steps-intraday']['dataset']:
                    steps_data.append({
                        'date': date,
                        'time': entry['time'],
                        'value': entry['value']
                    })
        logging.info(f"Fetched steps data: {len(steps_data)} entries")

        # Fetch heart rate data for both days
        heart_rate_data = []
        for date in [date_input, next_day]:
            heart_rate_response = get_heart_rate_intraday_data(ACCESS_TOKEN, date)
            if heart_rate_response and 'activities-heart-intraday' in heart_rate_response:
                for entry in heart_rate_response['activities-heart-intraday']['dataset']:
                    heart_rate_data.append({
                        'date': date,
                        'time': entry['time'],
                        'value': entry['value']
                    })
        logging.info(f"Fetched heart rate data: {len(heart_rate_data)} entries")

        # Fetch SpO2 data
        spo2_data = {}
        spo2_data[date_input] = get_spo2_intraday_data(ACCESS_TOKEN, date_input)
        spo2_data[next_day] = get_spo2_intraday_data(ACCESS_TOKEN, next_day)
        logging.info(f"Fetched SpO2 data: {sum(len(data.get('minutes', [])) for data in spo2_data.values() if data)} entries")

        if steps_data or heart_rate_data or spo2_data:
            logging.info("Combined Steps, Heart Rate, and SpO2 Intraday Data:")
            logging.info(f"Steps data: {len(steps_data)} entries")
            logging.info(f"Heart rate data: {len(heart_rate_data)} entries")
            logging.info(f"SpO2 data: {sum(len(data.get('minutes', [])) for data in spo2_data.values() if data)} entries")
        else:
            logging.warning("No Steps, Heart Rate, or SpO2 Intraday data found for the specified date and time range.")
         
        hrv_data = {}
        hrv_data[date_input] = get_hrv_intraday_data(ACCESS_TOKEN, date_input)
        hrv_data[next_day] = get_hrv_intraday_data(ACCESS_TOKEN, next_day)
        logging.info(f"Fetched HRV data: {sum(len(data.get('hrv', [])) for data in hrv_data.values() if data)} entries")

        if steps_data or heart_rate_data or spo2_data or hrv_data:
            logging.info("Combined Steps, Heart Rate, SpO2, and HRV Intraday Data:")
            logging.info(f"Steps data: {len(steps_data)} entries")
            logging.info(f"Heart rate data: {len(heart_rate_data)} entries")
            logging.info(f"SpO2 data: {sum(len(data.get('minutes', [])) for data in spo2_data.values() if data)} entries")
            logging.info(f"HRV data: {sum(len(data.get('hrv', [])) for data in hrv_data.values() if data)} entries")
        else:
            logging.warning("No Steps, Heart Rate, SpO2, or HRV Intraday data found for the specified date and time range.")

        sanitized_filename = sanitize_filename(f"activity_heart_spo2_hrv_data_{date_input}_22-00_to_{next_day}_22-00.csv")
        csv_filename = os.path.join(current_directory, sanitized_filename)
        logging.info(f"Saving combined data to {csv_filename}")
        save_combined_data_to_csv(device_id, steps_data, heart_rate_data, spo2_data, hrv_data, date_input, next_day, csv_filename)
        
    except ValueError:
        logging.error("Invalid date format. Please enter the date in YYYY-MM-DD format.")


        sanitized_filename = sanitize_filename(f"activity_heart_spo2_data_{date_input}_22-00_to_{next_day}_22-00.csv")
        csv_filename = os.path.join(current_directory, sanitized_filename)
        logging.info(f"Saving combined data to {csv_filename}")
        save_combined_data_to_csv(device_id, steps_data, heart_rate_data, spo2_data, date_input, next_day, csv_filename)
        
    except ValueError:
        logging.error("Invalid date format. Please enter the date in YYYY-MM-DD format.")
    
    ACCESS_TOKEN, REFRESH_TOKEN = check_and_refresh_tokens()
    if not ACCESS_TOKEN or not REFRESH_TOKEN:
        ACCESS_TOKEN, REFRESH_TOKEN = get_new_tokens()
        if not ACCESS_TOKEN or not REFRESH_TOKEN:
            logging.error("Failed to refresh or obtain new tokens. Exiting.")
            exit(1)
    save_tokens(ACCESS_TOKEN, REFRESH_TOKEN)