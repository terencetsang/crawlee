import json
import re
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Output directory for JSON files
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "odds_data")

def parse_url(url):
    """Parse HKJC odds URL to extract race details"""
    patterns = [
        r'https://bet\.hkjc\.com/ch/racing/wp/(\d{4}-\d{2}-\d{2})/(\w+)/(\d+)',
        r'https://bet\.hkjc\.com/ch/racing/pwin/(\d{4}-\d{2}-\d{2})/(\w+)/(\d+)'
    ]
    
    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            race_date = match.group(1)
            venue = match.group(2)
            race_number = int(match.group(3))
            return race_date, venue, race_number
    
    raise ValueError(f"Invalid HKJC odds URL format: {url}")

def get_hkjc_data(race_date, venue, race_number):
    """Get available data from HKJC for the specified race"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-HK,zh;q=0.9,en;q=0.8',
        'Referer': f'https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/{race_number}',
        'Origin': 'https://bet.hkjc.com',
    }
    
    result = {
        "race_info": {
            "race_date": race_date,
            "venue": venue,
            "race_number": race_number,
            "source_url": f"https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/{race_number}",
            "scraped_at": datetime.now().isoformat()
        },
        "betting_parameters": None,
        "odds_data": {
            "win_odds": None,
            "place_odds": None,
            "status": "not_available",
            "message": "Odds data requires JavaScript/authentication"
        },
        "available_endpoints": [],
        "summary": {
            "data_extraction_successful": False,
            "betting_parameters_available": False,
            "odds_data_available": False,
            "race_info_available": False
        }
    }
    
    # 1. Try to get betting parameters (this usually works)
    print("Getting betting parameters...")
    try:
        api_url = "https://txn01.hkjc.com/betslipIB/services/Para.svc/GetSP4EEwinPara"
        response = requests.get(api_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            try:
                text_data = response.text.lstrip('\ufeff')
                para_data = json.loads(text_data)
                result["betting_parameters"] = para_data
                result["summary"]["betting_parameters_available"] = True
                result["available_endpoints"].append({
                    "url": api_url,
                    "type": "betting_parameters",
                    "status": "success"
                })
                print("✓ Successfully got betting parameters")
            except json.JSONDecodeError:
                print("✗ Failed to parse betting parameters JSON")
        else:
            print(f"✗ Failed to get betting parameters: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"✗ Error getting betting parameters: {e}")
    
    # 2. Check if odds endpoints are accessible (they usually return HTML due to JS requirements)
    print("Checking odds endpoints...")
    odds_endpoints = [
        ("win_odds", f"https://bet.hkjc.com/racing/getodds.aspx?type=win&date={race_date}&venue={venue}&raceno={race_number}"),
        ("place_odds", f"https://bet.hkjc.com/racing/getodds.aspx?type=pla&date={race_date}&venue={venue}&raceno={race_number}")
    ]
    
    for odds_type, endpoint in odds_endpoints:
        try:
            response = requests.get(endpoint, headers=headers, timeout=15)
            if response.status_code == 200:
                result["available_endpoints"].append({
                    "url": endpoint,
                    "type": odds_type,
                    "status": "accessible_but_requires_js",
                    "note": "Returns HTML page that requires JavaScript"
                })
                print(f"✓ {odds_type} endpoint is accessible (but requires JS)")
            else:
                print(f"✗ {odds_type} endpoint returned HTTP {response.status_code}")
        except Exception as e:
            print(f"✗ Error checking {odds_type} endpoint: {e}")
    
    # 3. Try to get race information from the racing site
    print("Getting race information...")
    try:
        race_info_url = f"https://racing.hkjc.com/racing/information/Chinese/Racing/Racecard.aspx?RaceDate={race_date.replace('-', '/')}&Racecourse={venue}&RaceNo={race_number}"
        response = requests.get(race_info_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            result["available_endpoints"].append({
                "url": race_info_url,
                "type": "race_information",
                "status": "success"
            })
            result["summary"]["race_info_available"] = True
            print("✓ Race information page is accessible")
        else:
            print(f"✗ Race information page returned HTTP {response.status_code}")
            
    except Exception as e:
        print(f"✗ Error getting race information: {e}")
    
    # 4. Update summary
    result["summary"]["data_extraction_successful"] = any([
        result["summary"]["betting_parameters_available"],
        result["summary"]["race_info_available"]
    ])
    
    # 5. Add recommendations
    result["recommendations"] = {
        "for_odds_data": [
            "Use browser automation (Playwright/Selenium) with proper session management",
            "Consider using HKJC's official mobile app API if available",
            "Monitor network requests from the official website to find working API endpoints",
            "Use the betting parameters API to understand available bet types and limits"
        ],
        "working_endpoints": [
            "https://txn01.hkjc.com/betslipIB/services/Para.svc/GetSP4EEwinPara - Betting parameters",
            f"https://racing.hkjc.com/racing/information/Chinese/Racing/Racecard.aspx?RaceDate={race_date.replace('-', '/')}&Racecourse={venue}&RaceNo={race_number} - Race information"
        ]
    }
    
    return result

def save_data_to_json(data, race_date, venue, race_number):
    """Save the consolidated data to JSON file"""
    try:
        formatted_date = race_date.replace('-', '_')
        json_filename = f"{OUTPUT_DIR}/hkjc_data_{formatted_date}_{venue}_R{race_number}.json"
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Successfully saved data to: {json_filename}")
        return json_filename
    except Exception as e:
        print(f"Error saving data to JSON: {str(e)}")
        return None

def main(url=None):
    """Main function to get HKJC data for a specific race"""
    if url is None:
        url = "https://bet.hkjc.com/ch/racing/pwin/2025-07-01/ST/1"
    
    try:
        race_date, venue, race_number = parse_url(url)
        
        print(f"Getting HKJC data for Race {race_number} on {race_date} at {venue}")
        print(f"Source URL: {url}")
        print("=" * 60)
        
        # Get all available data
        data = get_hkjc_data(race_date, venue, race_number)
        
        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY:")
        print(f"✓ Betting Parameters: {'Yes' if data['summary']['betting_parameters_available'] else 'No'}")
        print(f"✓ Race Information: {'Yes' if data['summary']['race_info_available'] else 'No'}")
        print(f"✓ Odds Data: {'No (requires JavaScript)' if not data['summary']['odds_data_available'] else 'Yes'}")
        print(f"✓ Available Endpoints: {len(data['available_endpoints'])}")
        
        if data['available_endpoints']:
            print("\nWorking Endpoints:")
            for endpoint in data['available_endpoints']:
                status_icon = "✓" if endpoint['status'] == 'success' else "⚠️"
                print(f"  {status_icon} {endpoint['type']}: {endpoint['status']}")
        
        print("\n--- Complete Data ---")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        print("--------------------\n")
        
        # Save to JSON file
        json_file = save_data_to_json(data, race_date, venue, race_number)
        
        if json_file:
            print(f"Data saved successfully to {json_file}")
            
            # Print next steps
            print("\n" + "=" * 60)
            print("NEXT STEPS:")
            print("1. The betting parameters API is working and provides useful data")
            print("2. For actual odds data, you'll need to use browser automation")
            print("3. The race information page is accessible for race details")
            print("4. Consider monitoring network requests from the official site")
            print("=" * 60)
        else:
            print("Failed to save data to JSON file")
            
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == '__main__':
    import sys
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    url = None
    if len(sys.argv) > 1:
        url = sys.argv[1]
    
    main(url)
