import asyncio
import json
import re
import os
import requests
from crawlee.playwright_crawler import PlaywrightCrawler, PlaywrightCrawlingContext
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Output directory for JSON files
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "odds_data")

async def scrape_odds(race_date, venue, race_number):
    """
    Scrape odds data from HKJC betting page
    race_date: format YYYY-MM-DD
    venue: ST or HV
    race_number: race number (1-12)
    """
    
    # Convert date format from YYYY-MM-DD to YYYY-MM-DD for URL
    target_url = f"https://bet.hkjc.com/ch/racing/wp/{race_date}/{venue}/{race_number}"
    
    print(f"Scraping odds from: {target_url}")
    
    # Create a PlaywrightCrawler instance (needed for JavaScript-heavy pages)
    crawler = PlaywrightCrawler(
        # Use headless mode for faster scraping
        headless=True,
        # Set timeout in seconds (not milliseconds)
        request_handler_timeout=30,
    )
    
    odds_data = {}
    
    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        context.log.info(f'Processing {context.request.url} ...')
        
        try:
            # Wait for the page to load completely
            await context.page.wait_for_load_state('networkidle')
            
            # Wait a bit more for dynamic content to load
            await context.page.wait_for_timeout(3000)
            
            # Extract race information
            race_info = await extract_race_info(context)
            
            # Extract Win/Place odds
            win_place_odds = await extract_win_place_odds(context)
            
            # Extract Quinella odds
            quinella_odds = await extract_quinella_odds(context)
            
            # Extract Quinella Place odds
            quinella_place_odds = await extract_quinella_place_odds(context)
            
            # Extract other exotic bets if available
            exotic_odds = await extract_exotic_odds(context)
            
            # Combine all odds data
            odds_data.update({
                "race_info": race_info,
                "win_place_odds": win_place_odds,
                "quinella_odds": quinella_odds,
                "quinella_place_odds": quinella_place_odds,
                "exotic_odds": exotic_odds,
                "scraped_at": datetime.now().isoformat(),
                "source_url": target_url
            })
            
            # Store the extracted data
            await context.push_data(odds_data)
            
        except Exception as e:
            context.log.error(f"Error extracting odds data: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Run the crawler
    await crawler.run([target_url])
    
    return odds_data

async def extract_race_info(context):
    """Extract basic race information from the odds page"""
    try:
        race_info = {}
        
        # Try to extract race title/name
        race_title_selector = 'h1, .race-title, .race-name'
        race_title = await context.page.text_content(race_title_selector)
        if race_title:
            race_info['race_title'] = race_title.strip()
        
        # Try to extract race time
        time_selector = '.race-time, .start-time'
        race_time = await context.page.text_content(time_selector)
        if race_time:
            race_info['race_time'] = race_time.strip()
        
        # Try to extract race status
        status_selector = '.race-status, .betting-status'
        race_status = await context.page.text_content(status_selector)
        if race_status:
            race_info['race_status'] = race_status.strip()
        
        return race_info
    except Exception as e:
        print(f"Error extracting race info: {str(e)}")
        return {}

async def extract_win_place_odds(context):
    """Extract Win and Place odds"""
    try:
        win_place_odds = []
        
        # Look for odds tables or containers
        # This selector might need adjustment based on actual page structure
        odds_rows = await context.page.query_selector_all('tr, .odds-row, .horse-odds')
        
        for row in odds_rows:
            try:
                # Extract horse number
                horse_num_elem = await row.query_selector('.horse-number, td:first-child')
                if not horse_num_elem:
                    continue
                    
                horse_number = await horse_num_elem.text_content()
                if not horse_number or not horse_number.strip().isdigit():
                    continue
                
                # Extract horse name
                horse_name_elem = await row.query_selector('.horse-name')
                horse_name = await horse_name_elem.text_content() if horse_name_elem else ""
                
                # Extract Win odds
                win_odds_elem = await row.query_selector('.win-odds, .odds-win')
                win_odds = await win_odds_elem.text_content() if win_odds_elem else ""
                
                # Extract Place odds
                place_odds_elem = await row.query_selector('.place-odds, .odds-place')
                place_odds = await place_odds_elem.text_content() if place_odds_elem else ""
                
                odds_entry = {
                    "horse_number": horse_number.strip(),
                    "horse_name": horse_name.strip(),
                    "win_odds": win_odds.strip(),
                    "place_odds": place_odds.strip()
                }
                
                win_place_odds.append(odds_entry)
                
            except Exception as e:
                continue
        
        return win_place_odds
    except Exception as e:
        print(f"Error extracting win/place odds: {str(e)}")
        return []

async def extract_quinella_odds(context):
    """Extract Quinella odds"""
    try:
        quinella_odds = []
        
        # Look for quinella odds table
        quinella_rows = await context.page.query_selector_all('.quinella-odds tr, .qin-odds tr')
        
        for row in quinella_rows:
            try:
                cells = await row.query_selector_all('td')
                if len(cells) >= 3:
                    combination = await cells[0].text_content()
                    odds = await cells[1].text_content()
                    
                    quinella_odds.append({
                        "combination": combination.strip(),
                        "odds": odds.strip()
                    })
            except Exception as e:
                continue
        
        return quinella_odds
    except Exception as e:
        print(f"Error extracting quinella odds: {str(e)}")
        return []

async def extract_quinella_place_odds(context):
    """Extract Quinella Place odds"""
    try:
        quinella_place_odds = []
        
        # Look for quinella place odds table
        qp_rows = await context.page.query_selector_all('.quinella-place-odds tr, .qpl-odds tr')
        
        for row in qp_rows:
            try:
                cells = await row.query_selector_all('td')
                if len(cells) >= 3:
                    combination = await cells[0].text_content()
                    odds = await cells[1].text_content()
                    
                    quinella_place_odds.append({
                        "combination": combination.strip(),
                        "odds": odds.strip()
                    })
            except Exception as e:
                continue
        
        return quinella_place_odds
    except Exception as e:
        print(f"Error extracting quinella place odds: {str(e)}")
        return []

async def extract_exotic_odds(context):
    """Extract other exotic bet odds (Tierce, Trio, etc.)"""
    try:
        exotic_odds = {}
        
        # Look for different types of exotic bets
        exotic_types = ['tierce', 'trio', 'first4', 'quartet']
        
        for bet_type in exotic_types:
            try:
                # Look for odds containers for each bet type
                odds_container = await context.page.query_selector(f'.{bet_type}-odds, .{bet_type}')
                if odds_container:
                    odds_text = await odds_container.text_content()
                    exotic_odds[bet_type] = odds_text.strip()
            except Exception as e:
                continue
        
        return exotic_odds
    except Exception as e:
        print(f"Error extracting exotic odds: {str(e)}")
        return {}

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

async def main(url=None):
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
        odds_data = await scrape_odds(race_date, venue, race_number)

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
    asyncio.run(main(url))
