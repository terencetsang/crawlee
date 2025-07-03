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
    # URL formats: 
    # https://bet.hkjc.com/ch/racing/wp/2025-07-01/ST/1
    # https://bet.hkjc.com/ch/racing/pwin/2025-07-01/ST/1
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

def try_api_endpoints(race_date, venue, race_number):
    """Try to access HKJC API endpoints directly"""
    
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
        "api_attempts": []
    }
    
    # Try the odds parameter API
    print("Trying odds parameter API...")
    try:
        api_url = "https://txn01.hkjc.com/betslipIB/services/Para.svc/GetSP4EEwinPara"
        response = requests.get(api_url, headers=headers, timeout=30)
        
        result = {
            "endpoint": api_url,
            "status_code": response.status_code,
            "success": response.status_code == 200
        }
        
        if response.status_code == 200:
            try:
                data = response.json()
                result["data"] = data
                print(f"✓ Success! Got data from {api_url}")
            except:
                result["data"] = response.text[:1000]  # Save first 1000 chars if not JSON
                print(f"✓ Got response from {api_url} but not JSON")
        else:
            result["error"] = f"HTTP {response.status_code}: {response.text[:500]}"
            print(f"✗ Failed: {api_url} returned {response.status_code}")
        
        results["api_attempts"].append(result)
        
    except Exception as e:
        results["api_attempts"].append({
            "endpoint": api_url,
            "error": str(e),
            "success": False
        })
        print(f"✗ Error accessing {api_url}: {str(e)}")
    
    # Try the GraphQL API
    print("Trying GraphQL API...")
    try:
        api_url = "https://consvc.hkjc.com/JCBW/api/graph"
        
        # Try a simple GraphQL query for race information
        graphql_queries = [
            {
                "query": "query { races { id date venue raceNumber } }",
                "variables": {}
            },
            {
                "query": f"query {{ race(date: \"{race_date}\", venue: \"{venue}\", number: {race_number}) {{ odds {{ horse win place }} }} }}",
                "variables": {}
            },
            {
                "query": "{ __schema { types { name } } }",  # Schema introspection
                "variables": {}
            }
        ]
        
        for i, query_data in enumerate(graphql_queries):
            try:
                response = requests.post(api_url, json=query_data, headers=headers, timeout=30)
                
                result = {
                    "endpoint": f"{api_url} (query {i+1})",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "query": query_data["query"][:100] + "..." if len(query_data["query"]) > 100 else query_data["query"]
                }
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        result["data"] = data
                        print(f"✓ Success! Got data from GraphQL query {i+1}")
                        # If we got data, no need to try more queries
                        if data and not data.get('errors'):
                            results["api_attempts"].append(result)
                            break
                    except:
                        result["data"] = response.text[:1000]
                        print(f"✓ Got response from GraphQL query {i+1} but not JSON")
                else:
                    result["error"] = f"HTTP {response.status_code}: {response.text[:500]}"
                    print(f"✗ Failed: GraphQL query {i+1} returned {response.status_code}")
                
                results["api_attempts"].append(result)
                
            except Exception as e:
                results["api_attempts"].append({
                    "endpoint": f"{api_url} (query {i+1})",
                    "error": str(e),
                    "success": False,
                    "query": query_data["query"][:100] + "..." if len(query_data["query"]) > 100 else query_data["query"]
                })
                print(f"✗ Error with GraphQL query {i+1}: {str(e)}")
        
    except Exception as e:
        print(f"✗ General error with GraphQL API: {str(e)}")
    
    # Try other potential endpoints
    print("Trying other potential endpoints...")
    other_endpoints = [
        f"https://bet.hkjc.com/api/racing/odds/{race_date}/{venue}/{race_number}",
        f"https://bet.hkjc.com/api/racing/race/{race_date}/{venue}/{race_number}",
        f"https://racing.hkjc.com/api/odds/{race_date}/{venue}/{race_number}",
        "https://bet.hkjc.com/api/racing/current",
        "https://racing.hkjc.com/api/racing/current"
    ]
    
    for endpoint in other_endpoints:
        try:
            response = requests.get(endpoint, headers=headers, timeout=15)
            
            result = {
                "endpoint": endpoint,
                "status_code": response.status_code,
                "success": response.status_code == 200
            }
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    result["data"] = data
                    print(f"✓ Success! Got data from {endpoint}")
                except:
                    result["data"] = response.text[:500]
                    print(f"✓ Got response from {endpoint} but not JSON")
            else:
                result["error"] = f"HTTP {response.status_code}"
                print(f"✗ Failed: {endpoint} returned {response.status_code}")
            
            results["api_attempts"].append(result)
            
        except Exception as e:
            results["api_attempts"].append({
                "endpoint": endpoint,
                "error": str(e),
                "success": False
            })
            print(f"✗ Error accessing {endpoint}: {str(e)}")
    
    return results

def save_odds_to_json(odds_data, race_date, venue, race_number):
    """Save odds data to JSON file"""
    try:
        # Format the race date for the filename (convert from YYYY-MM-DD to YYYY_MM_DD)
        formatted_date = race_date.replace('-', '_')
        
        # Create the filename
        json_filename = f"{OUTPUT_DIR}/odds_api_{formatted_date}_{venue}_R{race_number}.json"
        
        # Ensure the output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Save the data to the JSON file
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(odds_data, f, ensure_ascii=False, indent=2)
        
        print(f"Successfully saved API results to: {json_filename}")
        return json_filename
    except Exception as e:
        print(f"Error saving API results to JSON: {str(e)}")
        return None

def main(url=None):
    """Main function to try API endpoints for a specific race"""
    if url is None:
        # Default URL
        url = "https://bet.hkjc.com/ch/racing/pwin/2025-07-01/ST/1"
    
    try:
        # Parse the URL to extract race details
        race_date, venue, race_number = parse_url(url)
        
        print(f"Trying API endpoints for Race {race_number} on {race_date} at {venue}")
        print(f"Source URL: {url}")
        print("=" * 60)
        
        # Try API endpoints
        results = try_api_endpoints(race_date, venue, race_number)
        
        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY:")
        successful_attempts = [attempt for attempt in results["api_attempts"] if attempt.get("success")]
        print(f"Total API attempts: {len(results['api_attempts'])}")
        print(f"Successful attempts: {len(successful_attempts)}")
        
        if successful_attempts:
            print("\nSuccessful endpoints:")
            for attempt in successful_attempts:
                print(f"  ✓ {attempt['endpoint']}")
        
        # Print the full results
        print("\n--- Full API Results ---")
        print(json.dumps(results, ensure_ascii=False, indent=2))
        print("------------------------\n")
        
        # Save to JSON file
        json_file = save_odds_to_json(results, race_date, venue, race_number)
        
        if json_file:
            print(f"API results saved successfully to {json_file}")
        else:
            print("Failed to save API results to JSON file")
            
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
    
    # Run the API tester
    main(url)
