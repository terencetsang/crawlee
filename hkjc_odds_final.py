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

def get_hkjc_odds_data(race_date, venue, race_number):
    """Get odds data from HKJC APIs"""
    
    # Set up headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-HK,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': f'https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/{race_number}',
        'Origin': 'https://bet.hkjc.com',
    }
    
    results = {
        "race_date": race_date,
        "venue": venue,
        "race_number": race_number,
        "scraped_at": datetime.now().isoformat(),
        "source_url": f"https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/{race_number}",
        "odds_data": {},
        "api_responses": []
    }
    
    # 1. Get betting parameters
    print("Getting betting parameters...")
    try:
        api_url = "https://txn01.hkjc.com/betslipIB/services/Para.svc/GetSP4EEwinPara"
        response = requests.get(api_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            try:
                # The response might have a BOM, so let's clean it
                text_data = response.text.lstrip('\ufeff')
                para_data = json.loads(text_data)
                results["api_responses"].append({
                    "endpoint": api_url,
                    "status": "success",
                    "data": para_data
                })
                results["odds_data"]["betting_parameters"] = para_data
                print("✓ Successfully got betting parameters")
            except json.JSONDecodeError as e:
                print(f"✗ Failed to parse JSON from betting parameters: {e}")
                results["api_responses"].append({
                    "endpoint": api_url,
                    "status": "error",
                    "error": f"JSON decode error: {e}",
                    "raw_data": response.text[:1000]
                })
        else:
            print(f"✗ Failed to get betting parameters: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"✗ Error getting betting parameters: {e}")
    
    # 2. Try to get actual odds data using different endpoints
    print("Trying to get odds data...")
    
    # Format date for different API calls
    date_formats = [
        race_date,  # 2025-07-01
        race_date.replace('-', ''),  # 20250701
        race_date.replace('-', '/'),  # 2025/07/01
    ]
    
    # Try different odds endpoints
    odds_endpoints = [
        # Try different URL patterns that might work
        f"https://bet.hkjc.com/racing/getodds.aspx?type=win&date={race_date}&venue={venue}&raceno={race_number}",
        f"https://bet.hkjc.com/racing/getodds.aspx?type=pla&date={race_date}&venue={venue}&raceno={race_number}",
        f"https://racing.hkjc.com/racing/getodds.aspx?type=win&date={race_date}&venue={venue}&raceno={race_number}",
        f"https://racing.hkjc.com/racing/getodds.aspx?type=pla&date={race_date}&venue={venue}&raceno={race_number}",
        
        # Try API-style endpoints
        f"https://bet.hkjc.com/api/odds/win/{race_date}/{venue}/{race_number}",
        f"https://bet.hkjc.com/api/odds/place/{race_date}/{venue}/{race_number}",
        f"https://racing.hkjc.com/api/odds/win/{race_date}/{venue}/{race_number}",
        f"https://racing.hkjc.com/api/odds/place/{race_date}/{venue}/{race_number}",
        
        # Try with different date formats
        f"https://bet.hkjc.com/racing/odds/{race_date.replace('-', '')}/{venue}/{race_number}",
        f"https://racing.hkjc.com/racing/odds/{race_date.replace('-', '')}/{venue}/{race_number}",
    ]
    
    for endpoint in odds_endpoints:
        try:
            print(f"Trying: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=15)
            
            if response.status_code == 200:
                # Check if response is JSON
                try:
                    data = response.json()
                    results["api_responses"].append({
                        "endpoint": endpoint,
                        "status": "success",
                        "data": data
                    })
                    
                    # Try to identify what type of odds data this is
                    if "win" in endpoint.lower():
                        results["odds_data"]["win_odds"] = data
                    elif "place" in endpoint.lower() or "pla" in endpoint.lower():
                        results["odds_data"]["place_odds"] = data
                    else:
                        results["odds_data"]["general_odds"] = data
                    
                    print(f"✓ Success! Got JSON data from {endpoint}")
                    
                except json.JSONDecodeError:
                    # Not JSON, might be XML or HTML
                    content = response.text.strip()
                    if content.startswith('<?xml') or '<' in content[:100]:
                        # Might be XML data
                        results["api_responses"].append({
                            "endpoint": endpoint,
                            "status": "success_xml",
                            "data": content[:2000]  # Save first 2000 chars
                        })
                        print(f"✓ Got XML/HTML response from {endpoint}")
                    else:
                        # Plain text response
                        results["api_responses"].append({
                            "endpoint": endpoint,
                            "status": "success_text",
                            "data": content[:1000]  # Save first 1000 chars
                        })
                        print(f"✓ Got text response from {endpoint}")
            else:
                print(f"✗ HTTP {response.status_code} from {endpoint}")
                
        except Exception as e:
            print(f"✗ Error with {endpoint}: {e}")
            continue
    
    # 3. Try to get race information
    print("Trying to get race information...")
    race_info_endpoints = [
        f"https://racing.hkjc.com/racing/information/Chinese/Racing/Racecard.aspx?RaceDate={race_date.replace('-', '/')}&Racecourse={venue}&RaceNo={race_number}",
        f"https://bet.hkjc.com/racing/info/{race_date}/{venue}/{race_number}",
        f"https://racing.hkjc.com/racing/info/{race_date}/{venue}/{race_number}",
    ]
    
    for endpoint in race_info_endpoints:
        try:
            print(f"Trying race info: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=15)
            
            if response.status_code == 200:
                # For race info, we mainly expect HTML
                content = response.text
                results["api_responses"].append({
                    "endpoint": endpoint,
                    "status": "success_html",
                    "data": content[:2000]  # Save first 2000 chars for analysis
                })
                print(f"✓ Got race info from {endpoint}")
                break  # Only need one successful race info response
                
        except Exception as e:
            print(f"✗ Error with race info {endpoint}: {e}")
            continue
    
    return results

def save_odds_to_json(odds_data, race_date, venue, race_number):
    """Save odds data to JSON file"""
    try:
        # Format the race date for the filename
        formatted_date = race_date.replace('-', '_')
        
        # Create the filename
        json_filename = f"{OUTPUT_DIR}/odds_final_{formatted_date}_{venue}_R{race_number}.json"
        
        # Ensure the output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Save the data to the JSON file
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(odds_data, f, ensure_ascii=False, indent=2)
        
        print(f"Successfully saved odds data to: {json_filename}")
        return json_filename
    except Exception as e:
        print(f"Error saving odds data to JSON: {str(e)}")
        return None

def main(url=None):
    """Main function to get odds for a specific race"""
    if url is None:
        # Default URL
        url = "https://bet.hkjc.com/ch/racing/pwin/2025-07-01/ST/1"
    
    try:
        # Parse the URL to extract race details
        race_date, venue, race_number = parse_url(url)
        
        print(f"Getting odds for Race {race_number} on {race_date} at {venue}")
        print(f"Source URL: {url}")
        print("=" * 60)
        
        # Get odds data
        results = get_hkjc_odds_data(race_date, venue, race_number)
        
        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY:")
        successful_responses = [resp for resp in results["api_responses"] if resp["status"].startswith("success")]
        print(f"Total API attempts: {len(results['api_responses'])}")
        print(f"Successful responses: {len(successful_responses)}")
        
        if successful_responses:
            print("\nSuccessful endpoints:")
            for resp in successful_responses:
                print(f"  ✓ {resp['endpoint']} ({resp['status']})")
        
        # Check if we got any actual odds data
        odds_found = any(key in results["odds_data"] for key in ["win_odds", "place_odds", "general_odds"])
        if odds_found:
            print(f"\n🎉 SUCCESS: Found actual odds data!")
        else:
            print(f"\n⚠️  No direct odds data found, but got {len(successful_responses)} successful API responses")
        
        # Print the results (truncated for readability)
        print("\n--- Odds Data Results ---")
        print(json.dumps(results, ensure_ascii=False, indent=2)[:3000] + "..." if len(json.dumps(results)) > 3000 else json.dumps(results, ensure_ascii=False, indent=2))
        print("-------------------------\n")
        
        # Save to JSON file
        json_file = save_odds_to_json(results, race_date, venue, race_number)
        
        if json_file:
            print(f"Results saved successfully to {json_file}")
        else:
            print("Failed to save results to JSON file")
            
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == '__main__':
    import sys
    
    # Create the output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Check if URL is provided as command line argument
    url = None
    if len(sys.argv) > 1:
        url = sys.argv[1]
    
    # Run the odds scraper
    main(url)
