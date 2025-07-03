import json
import re
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Output directory for JSON files
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "odds_data")

def parse_url(url):
    """Parse HKJC odds URL to extract race details"""
    # URL format: https://bet.hkjc.com/ch/racing/wp/2025-07-01/ST/1
    pattern = r'https://bet\.hkjc\.com/ch/racing/wp/(\d{4}-\d{2}-\d{2})/(\w+)/(\d+)'
    match = re.match(pattern, url)
    
    if match:
        race_date = match.group(1)
        venue = match.group(2)
        race_number = int(match.group(3))
        return race_date, venue, race_number
    else:
        raise ValueError(f"Invalid HKJC odds URL format: {url}")

def scrape_odds_simple(url):
    """
    Simple approach to scrape odds data using requests and BeautifulSoup
    This might not work if the page heavily relies on JavaScript
    """
    
    try:
        race_date, venue, race_number = parse_url(url)
        
        print(f"Attempting to scrape odds from: {url}")
        
        # Set up headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-HK,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Make the request
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"Failed to fetch page: HTTP {response.status_code}")
            return None
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check if the page loaded properly (not just JavaScript error)
        if "You need to enable JavaScript" in response.text:
            print("Page requires JavaScript - simple scraping won't work")
            print("The page content is dynamically loaded with JavaScript")
            
            # Try to extract any static data that might be available
            odds_data = {
                "error": "Page requires JavaScript for dynamic content",
                "race_date": race_date,
                "venue": venue,
                "race_number": race_number,
                "scraped_at": datetime.now().isoformat(),
                "source_url": url,
                "page_title": soup.title.string if soup.title else "No title",
                "static_content_available": False
            }
            
            return odds_data
        
        # If we get here, try to extract any available data
        odds_data = {
            "race_date": race_date,
            "venue": venue,
            "race_number": race_number,
            "scraped_at": datetime.now().isoformat(),
            "source_url": url
        }
        
        # Try to extract basic page information
        if soup.title:
            odds_data["page_title"] = soup.title.string
        
        # Look for any race information in the static HTML
        race_info = extract_static_race_info(soup)
        if race_info:
            odds_data["race_info"] = race_info
        
        # Look for any odds data in the static HTML
        static_odds = extract_static_odds(soup)
        if static_odds:
            odds_data["static_odds"] = static_odds
        
        # Check if we found any meaningful data
        if len(odds_data) > 6:  # More than just the basic fields
            odds_data["static_content_available"] = True
        else:
            odds_data["static_content_available"] = False
            odds_data["note"] = "No static odds data found - page likely requires JavaScript"
        
        return odds_data
        
    except Exception as e:
        print(f"Error scraping odds: {str(e)}")
        return {
            "error": str(e),
            "scraped_at": datetime.now().isoformat(),
            "source_url": url
        }

def extract_static_race_info(soup):
    """Extract any race information available in static HTML"""
    race_info = {}
    
    try:
        # Look for race title in various possible locations
        title_selectors = ['h1', 'h2', '.race-title', '.race-name', 'title']
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                race_info['title'] = element.get_text(strip=True)
                break
        
        # Look for any text containing race information
        page_text = soup.get_text()
        
        # Look for race time patterns
        time_patterns = [
            r'(\d{1,2}:\d{2})',
            r'開跑時間[：:]\s*(\d{1,2}:\d{2})',
            r'Race Time[：:]\s*(\d{1,2}:\d{2})'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, page_text)
            if match:
                race_info['race_time'] = match.group(1)
                break
        
        # Look for venue information
        if '沙田' in page_text:
            race_info['venue_chinese'] = '沙田'
        elif '跑馬地' in page_text:
            race_info['venue_chinese'] = '跑馬地'
        
        return race_info if race_info else None
        
    except Exception as e:
        print(f"Error extracting static race info: {str(e)}")
        return None

def extract_static_odds(soup):
    """Extract any odds data available in static HTML"""
    odds_data = {}
    
    try:
        # Look for tables that might contain odds
        tables = soup.find_all('table')
        
        for i, table in enumerate(tables):
            table_text = table.get_text()
            
            # Check if this table might contain odds
            if any(keyword in table_text for keyword in ['賠率', 'odds', '獨贏', 'Win', 'Place']):
                rows = table.find_all('tr')
                table_data = []
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if cells:
                        row_data = [cell.get_text(strip=True) for cell in cells]
                        if any(cell for cell in row_data):  # Skip empty rows
                            table_data.append(row_data)
                
                if table_data:
                    odds_data[f'table_{i+1}'] = table_data
        
        # Look for any div or span elements that might contain odds
        odds_elements = soup.find_all(['div', 'span'], class_=re.compile(r'odds|bet|win|place', re.I))
        
        if odds_elements:
            odds_texts = []
            for element in odds_elements:
                text = element.get_text(strip=True)
                if text and len(text) < 100:  # Avoid very long texts
                    odds_texts.append(text)
            
            if odds_texts:
                odds_data['odds_elements'] = odds_texts
        
        return odds_data if odds_data else None
        
    except Exception as e:
        print(f"Error extracting static odds: {str(e)}")
        return None

def save_odds_to_json(odds_data, race_date, venue, race_number):
    """Save odds data to JSON file"""
    try:
        # Format the race date for the filename (convert from YYYY-MM-DD to YYYY_MM_DD)
        formatted_date = race_date.replace('-', '_')
        
        # Create the filename
        json_filename = f"{OUTPUT_DIR}/odds_{formatted_date}_{venue}_R{race_number}.json"
        
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
    """Main function to scrape odds for a specific race"""
    if url is None:
        # Default URL from your request
        url = "https://bet.hkjc.com/ch/racing/wp/2025-07-01/ST/1"
    
    try:
        # Parse the URL to extract race details
        race_date, venue, race_number = parse_url(url)
        
        print(f"Scraping odds for Race {race_number} on {race_date} at {venue}")
        print(f"Source URL: {url}")
        
        # Scrape the odds data
        odds_data = scrape_odds_simple(url)
        
        if odds_data:
            # Print the extracted data
            print("\n--- Extracted Odds Data ---")
            print(json.dumps(odds_data, ensure_ascii=False, indent=2))
            print("---------------------------\n")
            
            # Save to JSON file
            json_file = save_odds_to_json(odds_data, race_date, venue, race_number)
            
            if json_file:
                print(f"Odds data saved successfully to {json_file}")
            else:
                print("Failed to save odds data to JSON file")
        else:
            print("No odds data was extracted")
            
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
    
    # Run the scraper
    main(url)
