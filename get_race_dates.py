#!/usr/bin/env python3
import requests
import json
from datetime import datetime

# Configuration
POCKETBASE_URL = "http://terence.myds.me:8081"
COLLECTION = "race_entries"

def get_all_race_dates():
    """Fetch all unique race dates from PocketBase."""
    try:
        # Construct the API URL to get race dates
        url = f"{POCKETBASE_URL}/api/collections/{COLLECTION}/records?fields=race_date&sort=-race_date"
        
        print(f"Fetching race dates from: {url}")
        
        # Make the request
        response = requests.get(url, headers={'Accept': 'application/json'})
        
        # Check if the request was successful
        if response.status_code != 200:
            print(f"Error: Received status code {response.status_code}")
            print(f"Response: {response.text}")
            return None
        
        # Parse the response
        data = response.json()
        
        if not data.get('items'):
            print("No items found in the response")
            return []
        
        # Extract unique race dates
        unique_dates = set()
        for item in data['items']:
            if 'race_date' in item and item['race_date']:
                unique_dates.add(item['race_date'])
        
        # Convert to list and sort (newest first)
        sorted_dates = sorted(list(unique_dates), key=lambda x: datetime.strptime(x, '%Y-%m-%d'), reverse=True)
        
        return sorted_dates
    
    except Exception as e:
        print(f"Error fetching race dates: {e}")
        return None

def main():
    # Get all race dates
    race_dates = get_all_race_dates()
    
    if race_dates is None:
        print("Failed to fetch race dates")
        return
    
    if not race_dates:
        print("No race dates found")
        return
    
    # Print the results
    print("\nAll Race Dates (newest first):")
    print("==============================")
    for date in race_dates:
        print(date)
    
    print(f"\nTotal unique race dates: {len(race_dates)}")
    
    # Generate HTML dropdown options
    print("\nHTML Dropdown Options:")
    print("=====================")
    options_html = ""
    for date in race_dates:
        options_html += f'<option value="{date}">{date}</option>\n'
    print(options_html)
    
    # Save to a file
    with open('race_dates.json', 'w') as f:
        json.dump(race_dates, f, indent=2)
    print("\nRace dates saved to race_dates.json")

if __name__ == "__main__":
    main()
