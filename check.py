import time
import requests
import yaml
import logging
import os
import subprocess
import sys

# Load the configuration from the YAML file
def load_config(file_path):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

# Configure logging
def configure_logging(debug_mode):
    level = logging.DEBUG if debug_mode else logging.INFO
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=level
    )

# Check if a spot is available in the event
def check_spot_availability(event_id, debug_mode):
    json_url = f"https://api.production.b81.io/api/events/{event_id}"
    try:
        response = requests.get(json_url)
        if response.status_code == 200:
            # Accessing the 'data' part of the JSON
            data = response.json().get('data', {})
            max_participants = data.get('max_participants')
            current_participants = data.get('current_participants_count')

            if debug_mode:
                logging.debug(f"Max participants: {max_participants}")
                logging.debug(f"Current participants: {current_participants}")

            if max_participants is not None and current_participants is not None:
                if current_participants < max_participants:
                    logging.info(f"Spot available! {current_participants}/{max_participants} participants.")
                    return True
                else:
                    logging.info(f"No spots available. {current_participants}/{max_participants} participants.")
                    return False
            else:
                logging.error("Couldn't find participant information in the JSON response.")
                return False
        else:
            logging.error(f"Failed to fetch the JSON data. Status code: {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return False

# Trigger macOS notification and bell sound
def notify_and_ring_bell():
    # Bell sound (macOS)
    os.system('say "Ding"')  # macOS TTS with a ding sound
    # macOS notification
    subprocess.run(["osascript", "-e", f'display notification "Spot Available!" with title "Event Notification"'])

# Send a POST request to the tickets API with event_id and user_id
def post_ticket(event_id, user_id, authorization_token):
    url = "https://api.production.b81.io/api/tickets"
    payload = {
        "event_id": event_id,
        "user_id": user_id
    }
    headers = {
        "Authorization": f"Bearer {authorization_token}"
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200 or response.status_code == 201:
            logging.info(f"Successfully posted to {url} with payload: {payload}")
        else:
            logging.error(f"Failed to POST to {url}. Status code: {response.status_code}. Response: {response.text}")
    except Exception as e:
        logging.error(f"An error occurred while posting: {e}")

def main():
    if len(sys.argv) < 2:
        logging.error("Please provide the path to the config file as the first command line argument.")
        return

    config_file = sys.argv[1]

    # Load configuration
    config = load_config(config_file)
    event_id = config['event_id']            # Event ID for constructing the event URL and for the ticket post
    user_id = config['user_id']              # User ID for the ticket post
    authorization_token = config['authorization_token']  # Authorization token for ticket post
    retry_delay = config['retry_delay']      # Retry delay in seconds
    debug_mode = config.get('debug', False)

    # Configure logging based on debug flag
    configure_logging(debug_mode)

    # Log the configuration if debugging is enabled
    logging.debug(f"Configuration: Event ID={event_id}, User ID={user_id}, Retry Delay={retry_delay}")

    # Continuously check for availability
    while True:
        logging.info(f"Checking spot availability for event {event_id}...")
        if check_spot_availability(event_id, debug_mode):
            logging.info("Spot available! Sending notification and posting ticket...")
            notify_and_ring_bell()
            post_ticket(event_id, user_id, authorization_token)
            return  # Exit once a spot is found and ticket is posted
        else:
            logging.info(f"No spots available. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)

if __name__ == "__main__":
    main()
